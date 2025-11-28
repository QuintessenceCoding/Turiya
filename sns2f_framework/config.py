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
    "https://en.wikipedia.org/wiki/Stigmergy",
    "https://www.holy-bhagavad-gita.org/chapter/1/",
    "https://www.holy-bhagavad-gita.org/chapter/2/",
    "https://www.holy-bhagavad-gita.org/chapter/3/",
    "https://www.holy-bhagavad-gita.org/chapter/4/",
    "https://www.holy-bhagavad-gita.org/chapter/5/",
    "https://www.holy-bhagavad-gita.org/chapter/6/",
    "https://www.holy-bhagavad-gita.org/chapter/7/",
    "https://www.holy-bhagavad-gita.org/chapter/8/",
    "https://www.holy-bhagavad-gita.org/chapter/9/",
    "https://www.holy-bhagavad-gita.org/chapter/10/",
    "https://www.holy-bhagavad-gita.org/chapter/11/",
    "https://www.holy-bhagavad-gita.org/chapter/12/",
    "https://www.holy-bhagavad-gita.org/chapter/13/",
    "https://www.holy-bhagavad-gita.org/chapter/14/",
    "https://www.holy-bhagavad-gita.org/chapter/15/",
    "https://www.holy-bhagavad-gita.org/chapter/16/",
    "https://www.holy-bhagavad-gita.org/chapter/17/",
    "https://www.holy-bhagavad-gita.org/chapter/18/",
    "https://www.himalayanacademy.com/book-reader/?book=/media/books/what-is-hinduism/what-is-hinduism.epub",
    "https://en.wikipedia.org/wiki/Special:Random",  # The classic random button
    "https://longreads.com/", # High quality journalism
    "https://aeon.co/" ,
           # Python Documentation (Structure and syntax)
    "https://docs.python.org/3/tutorial/index.html",
    "https://docs.python.org/3/library/index.html",
    
    # MDN Web Docs (Concepts of web and logic)
    "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
    
    # Real Python (Tutorial style, good for "How-to")
    "https://realpython.com/",   # Deep thinking essays
    # NASA (Clean text, high authority)
    "https://science.nasa.gov/universe/",
    "https://science.nasa.gov/solar-system/",
    
    # Nature Scitable (Education focused biology/genetics)
    "https://www.nature.com/scitable/topicpage/dna-replication-and-causes-of-mutation-409/",
    
    # Phys.org (Physics news and concepts)
    "https://phys.org/physics-news/",
    # Stanford Encyclopedia of Philosophy (The gold standard for logic)
    "https://plato.stanford.edu/entries/logic-ai/",
    "https://plato.stanford.edu/entries/reasoning-automated/",
    "https://plato.stanford.edu/entries/ethics-ai/",
    "https://plato.stanford.edu/entries/consciousness/",
    
    # Internet Encyclopedia of Philosophy
    "https://iep.utm.edu/category/science/",
    "https://iep.utm.edu/category/mind-and-cognitive-science/",
    # Wikipedia Portals (Better than random pages, focuses on core topics)
    "https://en.wikipedia.org/wiki/Portal:Science",
    "https://en.wikipedia.org/wiki/Portal:History",
    "https://en.wikipedia.org/wiki/Portal:Technology",
    "https://en.wikipedia.org/wiki/Portal:Mathematics",
    "https://en.wikipedia.org/wiki/Portal:Philosophy",
    
    # Britannica (High quality, concise)
    "https://www.britannica.com/topic/artificial-intelligence",
    "https://www.britannica.com/technology/computer-science"
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