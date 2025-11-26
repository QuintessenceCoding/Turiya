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
LOG_LEVEL = logging.DEBUG

# --- Learning ---
# Whitelisted sources for the PerceptionAgent to scan during learning
# In a real build, this would be a more complex config file.
WHITELISTED_SOURCES = [
    "httpss://en.wikipedia.org/wiki/Neuro-symbolic_AI",
    "httpss://en.wikipedia.org/wiki/Sparse_coding",
    "httpss://en.wikipedia.org/wiki/Knowledge_graph"
]

# --- Memory ---
STM_CAPACITY = 100  # Max items in Short-Term Memory
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2' # Lightweight, CPU-friendly model
EMBEDDING_DIMENSION = 384 # Dimension of the model above

# --- Agents ---
AGENT_SLEEP_INTERVAL = 0.1  # Seconds agents sleep in their processing loops