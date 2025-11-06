import streamlit as st
import pandas as pd
import sqlite3
import time
import plotly.express as px
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../regiguard.db")
DB_PATH = os.path.abspath(DB_PATH)


st.set_page_config(page_title="RegiGuard Monitor", layout="wide")
st.title("🛡️ RegiGuard Monitoring Dashboard")

@st.cache_data(ttl=30)
def load_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM querylog ORDER BY timestamp DESC", conn)
        conn.close()
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception as e:
        st.error(f"Failed to load DB: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No query logs yet. Generate some traffic first.")
    st.stop()

# ---- METRICS ----
total_queries = len(df)
avg_relevance = round(df["relevance_score"].mean(), 3)
avg_latency = round(df["latency_s"].mean(), 3)
feedback_counts = df["feedback"].value_counts().to_dict()

c1, c2, c3 = st.columns(3)
c1.metric("Total Queries", total_queries)
c2.metric("Avg Relevance", avg_relevance)
c3.metric("Avg Latency (s)", avg_latency)

# ---- CHARTS ----
st.subheader("Query Volume by Role")
role_chart = df["role"].value_counts().reset_index()
role_chart.columns = ["Role", "Count"]
st.plotly_chart(px.bar(role_chart, x="Role", y="Count", color="Role", title="Queries by Role"))

st.subheader("Relevance Score Over Time")
fig = px.line(df.sort_values("timestamp"), x="timestamp", y="relevance_score", markers=True)
st.plotly_chart(fig)

st.subheader("Feedback Distribution")
fb = df["feedback"].value_counts().reset_index()
fb.columns = ["Feedback", "Count"]
if not fb.empty:
    st.plotly_chart(px.pie(fb, names="Feedback", values="Count", title="Feedback Summary"))
else:
    st.info("No feedback recorded yet — interact with RegiGuard and submit feedback to populate this chart.")


# ---- Recent Logs ----
st.subheader("Recent Query Logs")
st.dataframe(
    df[["timestamp", "username", "role", "question", "relevance_score", "latency_s", "feedback"]].head(30),
    use_container_width=True
)

st.caption("🔄 Auto-refresh every 30 seconds (live mode)")
# Streamlit 1.50+ uses st.rerun(), older versions used experimental_rerun
try:
    import threading

    def auto_refresh(interval=30):
        def refresh():
            time.sleep(interval)
            if hasattr(st, "rerun"):
                st.rerun()
            elif hasattr(st, "experimental_rerun"):
                st.experimental_rerun()
        threading.Thread(target=refresh, daemon=True).start()

    auto_refresh(30)

except Exception as e:
    st.warning(f"Auto-refresh disabled: {e}")
