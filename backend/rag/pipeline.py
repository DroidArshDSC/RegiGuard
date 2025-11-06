from typing import List, Dict
from langchain_openai import ChatOpenAI
from sentence_transformers import SentenceTransformer, util
from .vectorstore import add_documents, query_vectorstore
import numpy as np
import os

# Reflection threshold for semantic similarity check
REFLECT_THRESHOLD = float(os.getenv("REFLECT_THRESHOLD", 0.5))


class RegiPipeline:
    def __init__(self):
        # Initialize LLM (LangChain wrapper for GPT models)
        # Uses your OPENAI_API_KEY from .env automatically
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        # Local sentence transformer for reflection/relevance check
        self.reflect_model = SentenceTransformer("all-MiniLM-L6-v2")

    def add_document(self, doc_id: str, text: str, access: str = "public", meta: dict | None = None):
        payload = {"id": doc_id, "text": text, "access": access, "meta": meta or {}}
        add_documents([payload])

    def plan(self, question: str) -> Dict:
        """Lightweight intent planning based on question keywords."""
        q = question.lower()
        if any(tok in q for tok in ["penalty", "fine", "penalties"]):
            intent = "penalty_lookup"
        elif any(tok in q for tok in ["deadline", "due date", "when is"]):
            intent = "deadline_lookup"
        else:
            intent = "general_lookup"
        return {"intent": intent}

    def retrieve(self, question: str, role: str, k: int = 3) -> List[Dict]:
        """Retrieve documents based on role access level."""
        allowed = ["public"] if role == "analyst" else ["public", "internal"]
        docs = query_vectorstore(question, k=k * 2, allowed_access=allowed)
        docs = sorted(docs, key=lambda d: d["score"])[:k]
        return docs

    def answer(self, question: str, docs: List[Dict]) -> str:
        """Generate an LLM answer using retrieved documents as context."""
        context = "\n\n".join([f"[{d['id']}]\n{d['text']}" for d in docs]) if docs else ""
        prompt = (
            "You are RegiGuard, a compliance assistant. "
            "Use ONLY the provided context to answer the question.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Provide a concise answer (2–6 sentences). "
            "At the end, list source ids in square brackets like [doc_id]."
        )
        # Use .invoke() for LangChain 1.x models
        response = self.llm.invoke(prompt)
        return response.content.strip()

    def reflect(self, question: str, docs: List[Dict]) -> Dict:
        """Validate retrieval quality via cosine similarity reflection."""
        if not docs:
            return {"relevance": 0.0, "ok": False}

        q_emb = self.reflect_model.encode(question, convert_to_tensor=True)
        doc_texts = [d["text"] for d in docs]
        doc_embs = self.reflect_model.encode(doc_texts, convert_to_tensor=True)
        sims = util.pytorch_cos_sim(q_emb, doc_embs).cpu().numpy().flatten()
        max_sim = float(np.max(sims)) if len(sims) > 0 else 0.0
        ok = max_sim >= REFLECT_THRESHOLD
        return {"relevance": max_sim, "ok": ok}

    def run(self, question: str, role: str = "analyst", k: int = 3) -> Dict:
        """Full RAG cycle: plan → retrieve → answer → reflect."""
        plan = self.plan(question)
        docs = self.retrieve(question, role, k=k)
        answer = self.answer(question, docs)
        reflect_res = self.reflect(question, docs)

        return {
            "plan": plan,
            "docs": docs,
            "answer": answer,
            "relevance": reflect_res["relevance"],
            "ok": reflect_res["ok"],
        }
