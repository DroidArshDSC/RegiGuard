# Get Started

## RegiGuard — Setup & Run Guide

RegiGuard is a Role-Based Compliance RAG System powered by FastAPI, LangChain, and Streamlit.
Follow these steps to set it up and run both backend and frontend environments locally in VS Code.

## 1. Prerequisites
Make sure you have the following installed:
- Python 3.11
- pip (comes with Python)
- VS Code

Recommended VS Code extensions:
- Python
- Pylance
- Code Runner (optional for quick script runs)

## 2. Environment Setup

```bash
# Clone the repository
git clone <your-regiguard-repo-url>
cd RegiGuard

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# or
source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

## 3. Environment Variables

Create a .env file in the project root with:
```bash
OPENAI_API_KEY=sk-proj-your-key
DATABASE_URL=sqlite:///./regiguard.db
JWT_SECRET=replace_with_a_secure_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
CHROMA_DIR=./chroma_db
```

## 4. Seed Initial Data

This step resets and seeds your local database and vectorstore.
Open a new terminal in VS Code, ensure the virtual environment is active, then run:

```python
python -m scripts.reset_and_seed
```

## 5. Run Backend (FastAPI)

In Terminal #1 in VS Code:
```python
uvicorn backend.main:app --reload --port 8000
```

API is now live at: http://127.0.0.1:8000/docs

## 6. Run Frontend (Streamlit)

Open Terminal #2 in VS Code and run:
```python
streamlit run frontend/app.py --server.port 8501
```

Frontend launches automatically at:
👉 http://localhost:8501

## 7. Default Credentials
| Role    | Username  | Password      | Permissions              |
| ------- | --------- | ------------- | ------------------------ |
| Admin   | `admin`   | `adminpass`   | Full (query + upload KB) |
| Officer | `officer` | `officerpass` | Query only               |
| Analyst | `analyst` | `analystpass` | Query only               |

## 9. Recommended VS Code Terminal Layout

Open two integrated terminals in VS Code:
| Terminal | Purpose  | Command                                            |
| -------- | -------- | -------------------------------------------------- |
| 1️⃣      | Backend  | `uvicorn backend.main:app --reload --port 8000`    |
| 2️⃣      | Frontend | `streamlit run frontend/app.py --server.port 8501` |

## 10. Optional: Reset Everything Later

If you ever want to rebuild from scratch:
```python
python -m scripts.reset_and_seed
```