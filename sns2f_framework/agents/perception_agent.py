# sns2f_framework/agents/perception_agent.py

import logging
import time
import random
import requests
import os
from bs4 import BeautifulSoup
from collections import deque
from urllib.parse import urljoin
from ddgs import DDGS

from sns2f_framework.agents.base_agent import BaseAgent
from sns2f_framework.core.event_bus import (
    EventBus, EVENT_START_LEARNING, EVENT_STOP_LEARNING, 
    EVENT_PERCEPTION_NEW_DATA, EVENT_GAP_DETECTED
)
from sns2f_framework.memory.memory_manager import MemoryManager
from sns2f_framework.config import WHITELISTED_SOURCES, DB_PATH, DEFAULT_CRAWL_MODE, TRUSTED_DOMAINS, LOW_QUALITY_DOMAINS
from sns2f_framework.core.trace_manager import trace_manager

log = logging.getLogger(__name__)

class PerceptionAgent(BaseAgent):
    """
    The Explorer (V6.0: Pirate Mode).
    - No Robots.txt checks.
    - Real Browser User-Agent.
    - Open Web capable.
    """

    def __init__(self, name: str, event_bus: EventBus, memory_manager: MemoryManager):
        super().__init__(name, event_bus)
        self.memory_manager = memory_manager
        self._is_learning = False
        
        self.crawl_mode = DEFAULT_CRAWL_MODE
        
        self.interest_queue = deque()
        self.frontier = deque()
        self.visited_urls = set()
        self.visited_topics = set()
        
        # Configuration

        self.db_limit_mb = 500  # Stop learning if DB exceeds 500MB

        

        self.seeds = [
            # --- CORE STEM ---
            "Mathematics", "Algebra", "Geometry", "Trigonometry", "Calculus",
            "Statistics", "Probability", "Number Theory", "Topology",
            "Linear Algebra", "Discrete Mathematics", "Logic", "Set Theory",

            # --- PHYSICS ---
            "Physics", "Classical Mechanics", "Quantum Mechanics",
            "Thermodynamics", "Electromagnetism", "Relativity",
            "Nuclear Physics", "Particle Physics", "Astrophysics",

            # --- CHEMISTRY ---
            "Chemistry", "Organic Chemistry", "Inorganic Chemistry",
            "Physical Chemistry", "Biochemistry", "Materials Science",

            # --- BIOLOGY ---
            "Biology", "Genetics", "Evolution", "Microbiology",
            "Neuroscience", "Botany", "Zoology", "Ecology",
            "Cell Biology", "Biotechnology", "Physiology",

            # --- EARTH & SPACE ---
            "Astronomy", "Cosmology", "Planetary Science", "Space Exploration",
            "Geology", "Meteorology", "Climatology", "Oceanography",

            # --- COMPUTER SCIENCE & TECH ---
            "Computer Science", "Algorithms", "Data Structures",
            "Artificial Intelligence", "Machine Learning", "Neural Networks",
            "Robotics", "Cryptography", "Cybersecurity", "Operating Systems",
            "Computer Architecture", "Networking", "Databases", "Programming Languages",
            "Software Engineering", "Distributed Systems",

            # --- SOCIAL SCIENCES ---
            "History", "World War I", "World War II", "Cold War",
            "Ancient Egypt", "Ancient Greece", "Ancient India", "Roman Empire",
            "Chinese History", "Medieval Europe", "Renaissance",
            "Sociology", "Criminology", "Anthropology", "Linguistics",
            "Feminism", "Women's Rights", "Social Justice", "Cultural Studies",
            "Economics", "Microeconomics", "Macroeconomics",
            "Game Theory", "Finance", "Trade", "Development Economics",
            "Psychology", "Cognitive Psychology", "Behavioral Psychology",
            "Developmental Psychology", "Neuroscience Psychology",
            "Political Science", "Governance", "Diplomacy",
            "International Relations", "Constitutional Law", "Public Policy",
            "Geography", "Human Geography", "Physical Geography",
            "Maps", "Countries", "Cultures", "Civilizations",

            # --- HUMANITIES ---
            "Philosophy", "Metaphysics", "Epistemology", "Ethics",
            "Logic", "Aesthetics", "Political Philosophy",
            "Philosophers", "Indian Philosophy", "Greek Philosophy",
            "Literature", "Poetry", "Novels", "Drama",
            "Mythology", "Folklore", "Comparative Literature",
            "Religion", "Hinduism", "Buddhism", "Christianity",
            "Islam", "Judaism", "Spirituality",
            "Art", "Painting", "Sculpture", "Architecture",
            "Music", "Dance", "Film", "Photography",
            "Culture", "Languages", "Traditions", "Myths",

            # --- APPLIED SCIENCES ---
            "Engineering", "Mechanical Engineering", "Electrical Engineering",
            "Civil Engineering", "Aerospace Engineering", "Biomedical Engineering",
            "Medicine", "Anatomy", "Diseases", "Pharmacology",
            "Surgery", "Public Health", "Nutrition",

            # --- GLOBAL KNOWLEDGE ---
            "Countries", "Cities", "Landmarks", "UNESCO Heritage Sites",
            "World Leaders", "Nobel Prize", "Scientific Discoveries",

            # --- META DOMAINS ---
            "Education", "Law", "Ethics", "Innovation", "Invention",
            "Human Behavior", "Society", "Civilization", "Environment",

            # --- ABSTRACT TOPICS ---
            "Consciousness", "Mind", "Intelligence", "Reality",
            "Time", "Space", "Life", "Existence",

            # --- HINDUISM FOCUS (placeholders, enable as needed) ---
            # "Hinduism", "Sanatana Dharma", "Vedas", "Upanishads", "Bhagavad Gita",
            # "Mahabharata", "Ramayana", "Vedanta", "Advaita Vedanta", ...
        ]
        
        # Minimal blocklist (Just binary files and malware/porn)
        self.blocked_keywords = [
            ".pdf", ".jpg", ".png", ".zip", ".exe", ".mp4", 
            "login", "signup", "register", "cart", "checkout", 
            "pornhub", "xvideos", "casino", "betting"
        ]
        
        self.subscribe(EVENT_START_LEARNING, self._on_start_learning)
        self.subscribe(EVENT_STOP_LEARNING, self._on_stop_learning)
        self.subscribe(EVENT_GAP_DETECTED, self._on_gap_detected)

    def set_mode(self, mode: str):
        if mode in ["strict", "safe", "open"]:
            self.crawl_mode = mode
            log.info(f"[{self.name}] Switched Crawl Mode to: {mode.upper()}")

    def _on_start_learning(self):
        self._is_learning = True

    def _on_stop_learning(self):
        self._is_learning = False

    def _on_gap_detected(self, topic: str, request_id: str = None):
        # Fix: Allow re-learning if it didn't stick the first time
        # if topic.lower() in self.visited_topics: return 
        
        log.info(f"[{self.name}] Curiosity Triggered! Priority: '{topic}'")
        self.interest_queue.append({'topic': topic, 'req_id': request_id})
        self.visited_topics.add(topic.lower())
        
        if not self._is_learning:
            self._is_learning = True
            self.publish(EVENT_START_LEARNING)

    def process_step(self):
        if not self._is_learning: return

        # 1. DB Health Check
        try:
            if os.path.exists(DB_PATH):
                size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
                if size_mb > self.db_limit_mb:
                    log.warning(f"[{self.name}] 🛑 DB Limit Reached. Pausing.")
                    self._is_learning = False
                    self.publish(EVENT_STOP_LEARNING)
                    return
        except: pass

        # 2. RAM Cleanup
        if len(self.visited_urls) > 5000:
            self.visited_urls.clear()

        url_to_scrape = None
        req_id = None
        
        # 3. Priority Hunt
        if self.interest_queue:
            item = self.interest_queue.popleft()
            topic = item['topic']
            req_id = item['req_id']
            log.info(f"[{self.name}] Hunting ({self.crawl_mode}): '{topic}'")
            url_to_scrape = self._search_for_topic(topic, req_id)
        
        # 4. Frontier
        elif self.frontier:
            url_to_scrape = self.frontier.popleft()
            if url_to_scrape in self.visited_urls:
                url_to_scrape = None

        # 5. Seed Reset
        if not url_to_scrape and not self.frontier:
             seed = random.choice(self.seeds)
             log.info(f"[{self.name}] Frontier empty. Searching seed: {seed}")
             url_to_scrape = self._search_for_topic(seed, None)

        # Execute
        if url_to_scrape:
            self.visited_urls.add(url_to_scrape)
            self._process_url(url_to_scrape, req_id)
        
        # Jitter
        time.sleep(random.uniform(2.0, 4.0))

    def _is_safe_url(self, url: str) -> bool:
        url_lower = url.lower()
        if any(bad in url_lower for bad in self.blocked_keywords): return False
        
        if self.crawl_mode == "strict":
            return any(trust in url_lower for trust in TRUSTED_DOMAINS)
        elif self.crawl_mode == "safe":
            return not any(bad in url_lower for bad in LOW_QUALITY_DOMAINS)
            
        return True

    def _process_url(self, url: str, req_id: str = None):
        if not self._is_safe_url(url): return

        # No Robots Check here anymore!
        
        observations, links = self._scrape_url_and_links(url)
        
        if observations:
            log.info(f"[{self.name}] Extracted {len(observations)} chunks from {url}")
            trace_manager.record(req_id, self.name, "Scraping Complete", f"Source: {url}")
            
            for text_chunk in observations:
                if not self._is_learning: break
                self.memory_manager.add_observation(text_chunk, source=url)
                self.publish(EVENT_PERCEPTION_NEW_DATA, source=url)
            
            for link in links:
                if link not in self.visited_urls and len(self.frontier) < 500:
                    if self._is_safe_url(link):
                        self.frontier.append(link)

    def _scrape_url_and_links(self, url: str):
        try:
            # Real Browser User-Agent (Spoofing Chrome)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5'
            }
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code != 200: return [], []

            soup = BeautifulSoup(response.content, 'html.parser')
            for junk in soup(["script", "style", "nav", "footer", "header", "form", "aside", "iframe", "noscript"]):
                junk.decompose()

            paragraphs = soup.find_all('p')
            cleaned_text = []
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 80: cleaned_text.append(text)
            
            if len(cleaned_text) < 2: return [], []

            new_links = []
            for a in soup.find_all('a', href=True):
                full_url = urljoin(url, a['href'])
                if full_url.startswith("http"):
                    new_links.append(full_url)
            
            random.shuffle(new_links)
            return cleaned_text[:25], new_links[:8]

        except Exception as e:
            # log.error(f"Scraping error: {e}") 
            return [], []

    def _search_for_topic(self, topic: str, req_id: str) -> str:
        try:
            # Pure search (no wiki bias unless strict)
            query = topic
            if self.crawl_mode == "strict":
                query += " site:wikipedia.org"
                
            results = DDGS().text(query, max_results=3)
            
            if results:
                for res in results:
                    url = res.get('href') or res.get('link') or res.get('url')
                    if url and self._is_safe_url(url):
                        log.info(f"[{self.name}] Found source: {url}")
                        trace_manager.record(req_id, self.name, "Web Search Success", url)
                        return url
            return None
        except:
            return None