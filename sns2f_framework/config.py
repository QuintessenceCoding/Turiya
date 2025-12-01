# sns2f_framework/config.py

import os
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "SNS2F (Hybrid Edition)"

DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'sns2f_memory.sqlite')
LOG_PATH = os.path.join(DATA_DIR, 'logs', 'system.log')
MODEL_DIR = os.path.join(DATA_DIR, 'models')

# TinyLlama (Fast, decent editor)
MODEL_REPO = "microsoft/Phi-3-mini-4k-instruct-gguf"
MODEL_FILENAME = "Phi-3-mini-4k-instruct-q4.gguf"

LOG_LEVEL = logging.INFO

# --- CRAWLER / LEARNING SETTINGS ---
DEFAULT_CRAWL_MODE = "safe"

# Fallback sources if search fails
WHITELISTED_SOURCES = [
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://en.wikipedia.org/wiki/Machine_learning",
    "https://en.wikipedia.org/wiki/Cognitive_science",
    "https://en.wikipedia.org/wiki/Neuro-symbolic_AI"
]

# STRICT/SAFE MODE DOMAINS (High Quality)
TRUSTED_DOMAINS = [
    "wikipedia.org", ".edu", ".gov", "arxiv.org", "britannica.com", 
    "nature.com", "nasa.gov", "phys.org", "sciencedaily.com", 
    "gutenberg.org", "smithsonianmag.com", "nationalgeographic.com",
    "ieee.org", "ncbi.nlm.nih.gov"
]

# SAFE MODE BLOCKLIST (Low Quality/User Generated)
LOW_QUALITY_DOMAINS = [
    "reddit.com", "quora.com", "twitter.com", "x.com", 
    "facebook.com", "instagram.com", "tiktok.com",
    "pinterest.com", "blogspot.com", "wordpress.com", "medium.com"
]

STM_CAPACITY = 100
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
EMBEDDING_DIMENSION = 384
AGENT_SLEEP_INTERVAL = 0.1