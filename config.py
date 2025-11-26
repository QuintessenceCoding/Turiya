import os
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
EMBEDDING_DIMENSION = 384
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'sns2f_memory.sqlite')
LOG_PATH = os.path.join(DATA_DIR, 'logs', 'system.log')
CHECKPOINT_DIR = os.path.join(DATA_DIR, 'checkpoints')
WHITELISTED_SOURCES = []
STM_CAPACITY = 100
AGENT_SLEEP_INTERVAL = 0.1
