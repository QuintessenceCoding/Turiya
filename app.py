# app.py

import streamlit as st
import time
import uuid
import queue
import logging
from datetime import datetime

# Import Turiya Framework
from sns2f_framework.core.orchestrator import Orchestrator
from sns2f_framework.core.trace_manager import trace_manager

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Turiya AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLING ---
st.markdown("""
<style>
    .stChatMessage { padding: 1rem; border-radius: 10px; }
    .stButton button { width: 100%; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- BACKEND SETUP (SINGLETON) ---
# This ensures the Orchestrator runs once and stays alive across UI reloads
@st.cache_resource
def get_system():
    print("--- 🚀 BOOTING TURIYA BACKEND ---")
    orchestrator = Orchestrator()
    orchestrator.start()
    
    # We need a thread-safe queue to pass messages from the Agent thread to the UI thread
    response_queue = queue.Queue()
    
    return orchestrator, response_queue

# Initialize System
orc, response_q = get_system()

# --- CALLBACK HANDLER ---
# This function runs in the background thread when the Agent replies
def ui_callback(response_text):
    response_q.put(response_text)

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "learning_active" not in st.session_state:
    st.session_state.learning_active = False
if "last_req_id" not in st.session_state:
    st.session_state.last_req_id = None
if "waiting_for_answer" not in st.session_state:
    st.session_state.waiting_for_answer = False

# --- SIDEBAR (MISSION CONTROL) ---
with st.sidebar:
    st.title("🧠 Turiya Controls")
    st.markdown("---")
    
    # Learning Controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ Start Learning", type="primary", disabled=st.session_state.learning_active):
            orc.start_learning()
            st.session_state.learning_active = True
            st.toast("Swarm is hunting for knowledge...", icon="🦅")
            st.rerun()
            
    with col2:
        if st.button("⏹ Stop", disabled=not st.session_state.learning_active):
            orc.stop_learning()
            st.session_state.learning_active = False
            st.toast("Learning paused.", icon="⏸")
            st.rerun()

    if st.session_state.learning_active:
        st.info("🟢 System Status: **LEARNING**")
    else:
        st.warning("🟠 System Status: **IDLE**")

    st.markdown("---")
    
    # Maintenance Controls
    if st.button("💎 Crystallize Concepts"):
        with st.spinner("Mining logic from raw facts..."):
            count = orc.consolidate_knowledge()
            st.success(f"Crystallized {count} new concepts!")
            
    if st.button("🌙 Sleep Cycle"):
        with st.spinner("Pruning unused memories..."):
            deleted = orc.sleep_cycle()
            st.success(f"Cleaned up {deleted} memories.")

    st.markdown("---")
    st.markdown("### 🔍 Thought Trace")
    if st.session_state.last_req_id:
        trace = trace_manager.get_trace(st.session_state.last_req_id)
        with st.expander("View Last Reasoning Chain", expanded=False):
            st.code(trace, language="text")
    else:
        st.caption("No recent activity.")

# --- MAIN CHAT INTERFACE ---
st.header("Chat with Turiya v2.2")

# 1. Display History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 2. Handle Input
if prompt := st.chat_input("Ask Turiya something..."):
    # Show User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate Request ID
    req_id = str(uuid.uuid4())
    st.session_state.last_req_id = req_id
    
    # Send to Backend
    st.session_state.waiting_for_answer = True
    orc.ask(prompt, ui_callback, request_id=req_id)
    st.rerun()

# 3. Handle Response (Polling loop)
if st.session_state.waiting_for_answer:
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # We poll the queue until an answer arrives
            # (Streamlit refreshes are handled by this loop)
            try:
                # Non-blocking check? No, we want to block this thread 
                # momentarily to wait for the result.
                # We wait in small chunks to allow UI to stay responsive-ish
                while response_q.empty():
                    time.sleep(0.1)
                
                # Get response
                response_text = response_q.get()
                st.markdown(response_text)
                
                # Save to history
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                st.session_state.waiting_for_answer = False
                st.rerun() # Refresh to update sidebar trace
                
            except Exception as e:
                st.error(f"Error receiving response: {e}")