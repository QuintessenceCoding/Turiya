# dashboard.py

import streamlit as st
import sqlite3
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import os
import time

# --- CONFIG ---
DB_PATH = os.path.join('sns2f_framework', 'data', 'sns2f_memory.sqlite')
st.set_page_config(page_title="SNS²F Control Room", layout="wide", page_icon="🧠")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .metric-card {
        background-color: #0E1117;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #262730;
        text-align: center;
    }
    .big-font { font-size: 30px !important; font-weight: bold; color: #00CCFF; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE HELPERS ---
def get_connection():
    if not os.path.exists(DB_PATH):
        return None
    # Connect in read-only mode to avoid locking the main agent
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

def load_stats():
    conn = get_connection()
    if not conn: return 0, 0, 0
    
    try:
        mem_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        con_count = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        fact_count = conn.execute("SELECT COUNT(*) FROM symbolic_knowledge").fetchone()[0]
        return mem_count, con_count, fact_count
    except:
        return 0, 0, 0
    finally:
        conn.close()

def load_graph_data(limit=50):
    """Fetch recent logic triples to build the graph."""
    conn = get_connection()
    if not conn: return []
    
    query = "SELECT subject, predicate, object FROM symbolic_knowledge ORDER BY id DESC LIMIT ?"
    try:
        rows = conn.execute(query, (limit,)).fetchall()
        return rows
    finally:
        conn.close()

def load_recent_logs():
    conn = get_connection()
    if not conn: return pd.DataFrame()
    query = "SELECT id, content, created_at FROM memories ORDER BY id DESC LIMIT 10"
    return pd.read_sql_query(query, conn)

# --- UI LAYOUT ---

st.title("🧠 Turiya: Neural Operations Center")
st.markdown("Real-time monitoring of the Self-Evolving Neuro-Symbolic Swarm.")

# 1. LIVE METRICS ROW
mem_count, con_count, fact_count = load_stats()

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f'<div class="metric-card"><h3>📚 Memories</h3><p class="big-font">{mem_count}</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><h3>💡 Concepts</h3><p class="big-font">{con_count}</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><h3>🕸️ Logic Facts</h3><p class="big-font">{fact_count}</p></div>', unsafe_allow_html=True)

st.divider()

# 2. MAIN VISUALIZATION TABS
tab1, tab2 = st.tabs(["🕸️ Knowledge Graph", "📜 Live Data Feed"])

with tab1:
    st.subheader("Visualizing the Logic Layer")
    
    # Graph Controls
    node_limit = st.slider("Max Facts to Visualize", 10, 200, 50)
    
    # Build Graph
    triples = load_graph_data(node_limit)
    
    if triples:
        G = nx.DiGraph()
        for subj, pred, obj in triples:
            # Shorten labels for cleaner viz
            s = (subj[:15] + '..') if len(subj) > 15 else subj
            o = (obj[:15] + '..') if len(obj) > 15 else obj
            G.add_edge(s, o, label=pred)

        # Plotting
        fig, ax = plt.subplots(figsize=(12, 8))
        pos = nx.spring_layout(G, k=0.5, seed=42)
        
        # Draw Nodes
        nx.draw_networkx_nodes(G, pos, node_size=2000, node_color="#4B4B4B", alpha=0.9)
        nx.draw_networkx_labels(G, pos, font_size=10, font_color="white", font_weight="bold")
        
        # Draw Edges
        nx.draw_networkx_edges(G, pos, edge_color="#00CCFF", alpha=0.5, arrows=True)
        edge_labels = nx.get_edge_attributes(G, 'label')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
        
        ax.set_facecolor("#0E1117") # Match Streamlit Dark Mode
        fig.patch.set_facecolor("#0E1117")
        plt.axis('off')
        
        st.pyplot(fig)
    else:
        st.info("No logic facts extracted yet. Run /start in the CLI to learn.")

with tab2:
    st.subheader("Recent Semantic Ingestions")
    df = load_recent_logs()
    if not df.empty:
        st.dataframe(df, width=None)
    else:
        st.write("Memory is empty.")

# Auto-refresh logic (Simple poll every 5s)
if st.button("🔄 Refresh Data"):
    st.rerun()