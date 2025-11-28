# sns2f_framework/config.py

import os
import logging

# --- General ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "SNS2F (Self-Evolving Neuro-Symbolic Swarm Framework)"

# --- Data Paths ---
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'sns2f_memory.sqlite')
LOG_PATH = os.path.join(DATA_DIR, 'logs', 'system.log')
CHECKPOINT_DIR = os.path.join(DATA_DIR, 'checkpoints')

# --- Logging ---
LOG_LEVEL = logging.INFO # Changed to INFO to keep CLI clean (DEBUG is too noisy for main.py)

# --- Learning ---
# Whitelisted sources for the PerceptionAgent to scan
WHITELISTED_SOURCES = [
    "https://en.wikipedia.org/wiki/Neuro-symbolic_AI",
    "https://en.wikipedia.org/wiki/Sparse_approximation",
    "https://en.wikipedia.org/wiki/Swarm_intelligence",
    "https://en.wikipedia.org/wiki/Artificial_neural_network",
    "https://en.wikipedia.org/wiki/Knowledge_graph",
    "https://en.wikipedia.org/wiki/Ant",
    "https://en.wikipedia.org/wiki/Stigmergy"
]

# --- Memory ---
STM_CAPACITY = 100  # Max items in Short-Term Memory
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2' # Lightweight, CPU-friendly model
EMBEDDING_DIMENSION = 384 # Dimension of the model above

# --- Agents ---
AGENT_SLEEP_INTERVAL = 0.1  # Seconds agents sleep in their processing loops

# --- Generative Model (The Brain) ---
# We store models in the data folder to keep the root clean
MODEL_DIR = os.path.join(DATA_DIR, 'models')

# OPTION 1: TinyLlama (Recommended for First Run) -> Fast, ~600MB
MODEL_REPO = "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"
MODEL_FILENAME = "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

# OPTION 2: Phi-3 (Smarter but Slower) -> ~2.4GB
# Uncomment these two lines below if you want to use the smarter model later
# MODEL_REPO = "microsoft/Phi-3-mini-4k-instruct-gguf"
# MODEL_FILENAME = "Phi-3-mini-4k-instruct-q4.gguf"