import os
import shutil
import time
from pathlib import Path
from backend.db import init_db, get_session_ctx   # ✅ fixed import
from backend.rag.vectorstore import add_documents
from backend.auth import hash_password
from backend.models import User

# --- Paths ---
DB_FILE = Path("regiguard.db")
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", "./chroma_db"))

# --- Clear DB and vectorstore ---
def clear_db_and_chroma():
    if DB_FILE.exists():
        DB_FILE.unlink()
        print("Removed regiguard.db")
    if CHROMA_DIR.exists() and CHROMA_DIR.is_dir():
        shutil.rmtree(CHROMA_DIR)
        print(f"Removed {CHROMA_DIR}")

# --- Seed docs and users ---
def seed():
    docs = [
        {
            "id": "gdpr_article5",
            "text": "Article 5 – Principles relating to processing of personal data. Data shall be processed lawfully, fairly and in a transparent manner.",
            "access": "public"
        },
        {
            "id": "mca_form8",
            "text": "MCA Form 8 filing penalty: late filing attracts fines; companies must file within X days or face penalties.",
            "access": "internal"
        },
        {
            "id": "sebi_disclosure",
            "text": "SEBI circular: listed entities must disclose price-sensitive information within prescribed timelines.",
            "access": "public"
        },
    ]

    add_documents(docs)
    print("Indexed sample docs")

    init_db()

    with get_session_ctx() as session:
        admin = User(username="admin", hashed_password=hash_password("adminpass"), role="admin")
        officer = User(username="officer", hashed_password=hash_password("officerpass"), role="officer")
        analyst = User(username="analyst", hashed_password=hash_password("analystpass"), role="analyst")
        session.add(admin)
        session.add(officer)
        session.add(analyst)
        session.commit()
    print("Created users: admin/officer/analyst")

# --- Entry point ---
if __name__ == "__main__":
    clear_db_and_chroma()
    time.sleep(0.3)  # avoid file lock on Windows
    seed()
