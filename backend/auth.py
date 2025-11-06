import os
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import select
from typing import Generator
from dotenv import load_dotenv

from .models import User
from .db import get_session_ctx

# --- Load environment variables early ---
load_dotenv()

# --- Password + Token Config ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

SECRET_KEY = os.getenv("JWT_SECRET", "devsecret_replace_me")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# --- Password helpers ---
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# --- JWT helpers ---
def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str:
    to_encode = {"sub": subject, "role": role}
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- User helpers ---
def get_user_by_username(username: str, session) -> User | None:
    stmt = select(User).where(User.username == username)
    return session.exec(stmt).first()

def authenticate_user(session, username: str, password: str):
    user = get_user_by_username(username, session)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

# --- Token verification ---
def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e

    with get_session_ctx() as session:
        user = get_user_by_username(username, session)
    if user is None:
        raise credentials_exception
    return user

# --- Role-based restriction helper ---
def require_role(allowed_roles: list):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return current_user
    return role_checker
