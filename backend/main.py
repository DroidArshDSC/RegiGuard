import os
import time
from typing import List
from datetime import datetime
from sqlmodel import Session
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from dotenv import load_dotenv  # <-- load .env early

# --- Load environment variables ---
load_dotenv()

# --- Internal imports ---
from backend.db import init_db, get_session, get_session_ctx
from backend.models import User, QueryLog, DocIn, QueryIn
from backend.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
)
from backend.rag.pipeline import RegiPipeline
from backend.rag.vectorstore import add_documents

# --- Initialize FastAPI ---
app = FastAPI(title="RegiGuard API", version="1.0")

# --- Middleware (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- RBAC Helper ---
def admin_required(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

# --- Startup ---
@app.on_event("startup")
def on_startup():
    init_db()
    app.state.pipeline = RegiPipeline()
    print("✅ RegiPipeline initialized")

# --- Root Healthcheck ---
@app.get("/")
def root():
    return {"status": "ok", "message": "RegiGuard backend active"}

# --- JWT Login ---
@app.post("/token")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.username, role=user.role)
    return {"access_token": access_token, "token_type": "bearer"}

# --- RAG Query Endpoint ---
@app.post("/query")
def query_endpoint(payload: QueryIn, current_user: User = Depends(get_current_user)):
    start = time.perf_counter()
    role = current_user.role

    pipeline: RegiPipeline = app.state.pipeline
    res = pipeline.run(payload.question, role=role, k=payload.max_docs)

    latency = time.perf_counter() - start

    # Log query details
    doc_versions = []
    for d in res.get("docs", []):
        v = d.get("metadata", {}).get("version")
        if v:
            doc_versions.append(f"{d.get('id')}@{v}")
    doc_versions_str = ";".join(doc_versions) if doc_versions else None

    with get_session_ctx() as session:
        qlog = QueryLog(
            username=current_user.username,
            role=role,
            question=payload.question,
            top_docs=";".join([d["id"] for d in res.get("docs", [])]) if res.get("docs") else None,
            relevance_score=res.get("relevance"),
            latency_s=round(latency, 3),
            doc_versions=doc_versions_str
        )
        session.add(qlog)
        session.commit()
        res["query_id"] = str(qlog.id)

    return res

# --- Feedback Endpoint ---
@app.post("/feedback")
def submit_feedback(data: dict, current_user: User = Depends(get_current_user)):
    query_id = data.get("query_id")
    feedback = data.get("feedback")
    comments = data.get("comments")

    if not query_id:
        raise HTTPException(status_code=400, detail="Query ID required")

    with get_session_ctx() as session:
        q = session.get(QueryLog, query_id)
        if not q:
            raise HTTPException(status_code=404, detail="Query not found")
        q.feedback = feedback
        q.feedback_comment = comments
        session.add(q)
        session.commit()

    return {"status": "recorded"}

# --- Admin: Batch Document Upload ---
@app.post("/admin/add_doc")
def add_doc(docs: List[DocIn], user: User = Depends(admin_required)):
    try:
        add_documents([d.dict() for d in docs])
        return {"ok": True, "count": len(docs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error indexing docs: {e}")

# --- Health Endpoint ---
@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}
