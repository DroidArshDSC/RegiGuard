import os
from sqlmodel import SQLModel, create_engine, Session
from contextlib import contextmanager
from dotenv import load_dotenv

# --- Load environment variables early ---
load_dotenv()

# --- Database Config ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./regiguard.db")
engine = create_engine(DATABASE_URL, echo=False)

# --- Initialize tables ---
def init_db():
    SQLModel.metadata.create_all(engine)

# --- FastAPI dependency (used in Depends) ---
def get_session():
    with Session(engine) as session:
        yield session

# --- Context manager for scripts/internal use ---
@contextmanager
def get_session_ctx():
    with Session(engine) as session:
        yield session
