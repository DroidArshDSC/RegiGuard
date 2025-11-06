import uuid
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

def gen_uuid() -> str:
    return str(uuid.uuid4())

# --- User Table ---
class User(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True, index=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    role: str  # 'admin' | 'officer' | 'analyst'

# --- Query Log Table ---
class QueryLog(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    username: str
    role: str
    question: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # monitoring fields
    top_docs: Optional[str] = None
    relevance_score: Optional[float] = None
    latency_s: Optional[float] = None
    doc_versions: Optional[str] = None

    # feedback fields
    feedback: Optional[str] = None             # 'useful' | 'wrong' | 'partial'
    feedback_comment: Optional[str] = None     # user-provided text/comment

# --- Request Schemas ---
class DocIn(SQLModel):
    id: str
    text: str
    access: str  # 'public' | 'internal'

class QueryIn(SQLModel):
    question: str
    max_docs: int = 3
