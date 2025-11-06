import streamlit as st
import requests
import json
import base64
from datetime import datetime
from io import BytesIO
from PyPDF2 import PdfReader
import docx

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="RegiGuard", layout="wide")
st.title("🛡️ RegiGuard — Compliance Intelligence")

# --- Session State Initialization ---
for key, val in {
    "token": None,
    "role": None,
    "chat_history": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- Auth Function ---
def login(username, password):
    try:
        r = requests.post(f"{API_URL}/token", data={"username": username, "password": password})
        if r.status_code == 200:
            data = r.json()
            token = data.get("access_token")
            st.session_state.token = token

            # Decode JWT payload for role (read-only)
            try:
                payload_part = token.split(".")[1]
                payload_part += "=" * (-len(payload_part) % 4)
                decoded = base64.urlsafe_b64decode(payload_part)
                payload_json = json.loads(decoded)
                st.session_state.role = payload_json.get("role", "unknown")
            except Exception:
                st.session_state.role = "unknown"

            st.success(f"Logged in as {username} ({st.session_state.role})")
            return True
        else:
            st.error("Invalid username or password.")
            return False
    except Exception as e:
        st.error(f"Login failed: {e}")
        return False

# --- Sidebar Login ---
st.sidebar.header("🔐 Authentication")
if not st.session_state.token:
    user = st.sidebar.text_input("Username")
    pw = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if login(user, pw):
            st.rerun()
else:
    st.sidebar.success(f"Authenticated as {st.session_state.role}")
    if st.sidebar.button("Logout"):
        st.session_state.token = None
        st.session_state.role = None
        st.session_state.chat_history = []
        st.rerun()

if not st.session_state.token:
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}", "Content-Type": "application/json"}

# --- Role-based Tabs ---
if st.session_state.role == "admin":
    tab1, tab2 = st.tabs(["💬 Query", "⚙️ Admin Tools"])
else:
    tab1, = st.tabs(["💬 Query"])

# --- Query Interface ---
with tab1:
    st.subheader("Ask RegiGuard")

    # Show recent chat history
    if st.session_state.chat_history:
        st.markdown("#### 🗂️ Chat History")
        for h in reversed(st.session_state.chat_history[-5:]):
            st.markdown(f"**[{h['time']}] You:** {h['question']}")
            st.markdown(f"**RegiGuard:** {h['answer']}")
            st.markdown("---")

    q = st.text_area("Enter your compliance query:")
    if st.button("Submit Query"):
        if not q.strip():
            st.warning("Enter a question.")
        else:
            r = requests.post(f"{API_URL}/query", headers=headers, json={"question": q})
            if r.status_code == 200:
                res = r.json()
                st.markdown("### 🧠 Answer")
                st.write(res.get("answer", ""))
                st.markdown(f"**Relevance:** {res.get('relevance', 0):.2f}")
                st.markdown(f"**Query ID:** `{res.get('query_id', 'N/A')}`")

                st.session_state.chat_history.append({
                    "question": q,
                    "answer": res.get("answer", ""),
                    "time": datetime.now().strftime("%H:%M:%S")
                })

                if res.get("docs"):
                    with st.expander("Retrieved Documents"):
                        for d in res["docs"]:
                            st.markdown(f"**{d['id']}** — {d['metadata'].get('access','public')}")
                            st.caption(d["text"])

                # --- Feedback ---
                st.markdown("### 🗳️ Feedback")
                cols = st.columns(3)
                qid = res.get("query_id")

                def send_feedback(label, value, comment):
                    requests.post(f"{API_URL}/feedback", headers=headers,
                                  json={"query_id": qid, "feedback": value, "comments": comment})
                    st.success(f"Feedback recorded: {label}")

                if cols[0].button("👍 Useful"):
                    send_feedback("useful", "useful", "accurate")
                if cols[1].button("🤔 Partial"):
                    send_feedback("partial", "partial", "somewhat relevant")
                if cols[2].button("👎 Wrong"):
                    send_feedback("wrong", "wrong", "off-topic")
            else:
                st.error(f"Error: {r.status_code} — {r.text}")

# --- Admin Tools (Admins Only) ---
if st.session_state.role == "admin":
    with tab2:
        st.subheader("🗂️ Knowledge Base Management")

        uploaded_files = st.file_uploader(
            "Upload one or more documents (TXT, PDF, DOCX)",
            type=["txt", "pdf", "docx"],
            accept_multiple_files=True
        )
        access = st.selectbox("Access Level", ["public", "internal"])

        if uploaded_files and st.button("Add Documents"):
            all_docs = []
            for file in uploaded_files:
                ext = file.name.split(".")[-1].lower()
                text = ""
                try:
                    if ext == "txt":
                        text = file.read().decode("utf-8")
                    elif ext == "pdf":
                        reader = PdfReader(BytesIO(file.read()))
                        text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
                    elif ext == "docx":
                        doc = docx.Document(BytesIO(file.read()))
                        text = "\n".join([p.text for p in doc.paragraphs])
                    all_docs.append({"id": file.name, "text": text, "access": access})
                except Exception as e:
                    st.error(f"Error reading {file.name}: {e}")

            if all_docs:
                r = requests.post(f"{API_URL}/admin/add_doc", headers=headers, json=all_docs)
                if r.status_code == 200:
                    st.success(f"Uploaded and indexed {len(all_docs)} document(s).")
                else:
                    st.error(f"Upload failed: {r.status_code} — {r.text}")
