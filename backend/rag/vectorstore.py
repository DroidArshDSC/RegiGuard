import os
import datetime
from typing import List
# modern LangChain provider imports 
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large")

def get_embeddings():
    """
    Try OpenAI embeddings first; on any failure, fall back to a HuggingFace sentence-transformer.
    """
    try:
        return OpenAIEmbeddings(model=EMBED_MODEL)
    except Exception as e:
        # fallback to local HuggingFace embeddings (offline)
        print(f"[RegiGuard] OpenAIEmbeddings failed, falling back to HuggingFace: {e}")
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def get_vectorstore(persist_directory: str = CHROMA_DIR):
    embeddings = get_embeddings()
    vs = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    return vs

def add_documents(documents: List[dict]):
    """
    documents: list of {"id": str, "text": str, "access": "public"|"internal", "meta": {...}}
    Each added doc will get a version timestamp in metadata.
    """
    vs = get_vectorstore()
    docs = []
    for d in documents:
        version = datetime.datetime.utcnow().isoformat()
        meta = {"id": d["id"], "access": d.get("access", "public"), "version": version}
        if d.get("meta"):
            meta.update(d["meta"])
        docs.append(Document(page_content=d["text"], metadata=meta))
    if docs:
        # Chroma may persist automatically; add_documents then persist is safe
        vs.add_documents(docs)
        try:
            vs.persist()
        except Exception:
            # some Chroma versions persist automatically; ignore persistence errors
            pass
    return True

def query_vectorstore(query: str, k: int = 3, allowed_access: list | None = None):
    """
    Returns list of dicts: {id, text, score, metadata}
    """
    vs = get_vectorstore()
    results = vs.similarity_search_with_score(query, k=k)
    out = []
    for doc, score in results:
        meta = dict(doc.metadata or {})
        access = meta.get("access", "public")
        if allowed_access and access not in allowed_access:
            continue
        out.append({
            "id": meta.get("id", "unknown"),
            "text": doc.page_content,
            "score": float(score),
            "metadata": meta
        })
    return out
