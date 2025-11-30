# sns2f_framework/agents/perception_agent.py

# sns2f_framework/agents/perception_agent.py

import logging
import time
import random
import requests
import os
from bs4 import BeautifulSoup
from collections import deque
from urllib.parse import urljoin
from duckduckgo_search import DDGS

from sns2f_framework.agents.base_agent import BaseAgent
from sns2f_framework.core.event_bus import (
    EventBus, EVENT_START_LEARNING, EVENT_STOP_LEARNING, 
    EVENT_PERCEPTION_NEW_DATA, EVENT_GAP_DETECTED
)
from sns2f_framework.memory.memory_manager import MemoryManager
from sns2f_framework.config import WHITELISTED_SOURCES, DB_PATH
from sns2f_framework.core.trace_manager import trace_manager

log = logging.getLogger(__name__)

class PerceptionAgent(BaseAgent):
    """
    The Explorer (V5.0: Long-Haul Safe).
    Features:
    - Strict Domain Filtering (No weird sites)
    - Database Size Guard (Prevents bloat)
    - Random Jitter (Politeness)
    - Logic fixes for topic tracking
    """

    def __init__(self, name: str, event_bus: EventBus, memory_manager: MemoryManager):
        super().__init__(name, event_bus)
        self.memory_manager = memory_manager
        self._is_learning = False
        
        # Queues
        self.interest_queue = deque()
        self.frontier = deque()
        
        # Memory Management (RAM)
        self.visited_urls = set()
        self.visited_topics = set()
        
        # Configuration
        self.db_limit_mb = 500  # Stop learning if DB exceeds 500MB
        
        self.seeds = [



     # --- CORE STEM ---

        "Mathematics", "Algebra", "Geometry", "Trigonometry", "Calculus",

        "Statistics", "Probability", "Number Theory", "Topology", 

        "Linear Algebra", "Discrete Mathematics", "Logic", "Set Theory", 



        "Physics", "Classical Mechanics", "Quantum Mechanics",

        "Thermodynamics", "Electromagnetism", "Relativity",

        "Nuclear Physics", "Particle Physics", "Astrophysics",



     "Chemistry", "Organic Chemistry", "Inorganic Chemistry",

        "Physical Chemistry", "Biochemistry", "Materials Science",



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

        "Islam", "Judaism", "Mythology", "Spirituality",



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



        # --- HIGH-LEVEL ABSTRACT TOPICS ---

        "Consciousness", "Mind", "Intelligence",

        "Reality", "Time", "Space", "Life", "Existence",



        #--- HINDUISM FOCUS ----

        # --- CORE FOUNDATIONAL TEXTS ---

        "Hinduism", "Sanatana Dharma",

        "Vedas", "Rigveda", "Yajurveda", "Samaveda", "Atharvaveda",

        "Upanishads", "Brahmanas", "Aranyakas",

        "Bhagavad Gita", "Mahabharata", "Ramayana",

        "Vedanta", "Advaita Vedanta", "Vishishtadvaita", "Dvaita", 

        "Puranas", "Bhagavata Purana", "Shiva Purana", "Vishnu Purana", "Devi Bhagavata",



        # --- SCHOOLS OF PHILOSOPHY (DARSHANAS) ---

        "Nyaya", "Vaisheshika", "Samkhya", "Yoga", "Mimamsa", "Purva Mimamsa", 

        "Uttara Mimamsa", "Charvaka",



        # --- METAPHYSICS & CORE CONCEPTS ---

        "Brahman", "Atman", "Maya", "Avidya", "Shakti",

        "Karma", "Dharma", "Artha", "Kama", "Moksha",

        "Samsara", "Reincarnation", "Purusha", "Prakriti",

        "Gunatraya", "Sattva", "Rajas", "Tamas",

        "Yugas", "Kali Yuga", "Dvapara Yuga", "Treta Yuga", "Satya Yuga",

        "Kundalini", "Chakras", "Tantra", "Mantra", "Yantra", "Agama Shastra",



        # --- MAJOR DEITIES & THEIR ASPECTS ---

        "Brahma", "Vishnu", "Shiva",

      "Devi", "Durga", "Kali", "Lakshmi", "Saraswati", "Parvati",

        "Ganesha", "Kartikeya", "Hanuman",

        "Krishna", "Rama", "Vishnu Avatars", "Dashavatara",



        # --- EPICS & ITIHASA ---

        "Mahabharata characters", "Ramayana characters",

        "Kurukshetra War", "Pandavas", "Kauravas",

        "Bhishma", "Drona", "Arjuna", "Karna",

        "Sita", "Ravana", "Valmiki", "Vyasa",



        # --- PURANIC COSMOLOGY ---

        "Hindu Cosmology", "Lokas", "Vaikuntha", "Kailasa", "Goloka",

        "Triloka", "Seven Lokas", "Fourteen Lokas",

        "Hindu Creation Myths", "Pralaya", "Kalpas", "Manvantaras",



        # --- RITUALS & PRACTICES ---

        "Puja", "Yajna", "Homa", "Aarti",

        "Vrata", "Samskaras", "Hindu Temple Rituals",

        "Meditation in Hinduism", "Bhakti Yoga", "Jnana Yoga", "Karma Yoga", "Raja Yoga",

        "Ayurveda", "Sanskrit", "Panchangam", "Jyotisha", "Hindu Astrology",



        # --- SECTS & TRADITIONS ---

        "Shaivism", "Shaktism", "Vaishnavism", "Smartism",

        "Puranic Hinduism", "Tantric Hinduism", "Bhakti Movement",
        "Dvaita tradition", "Advaita tradition", "Gaudiya Vaishnavism",

        "Nath tradition", "Aghoris", "Lingayatism",



        # --- FAMOUS SAINTS, GURUS & PHILOSOPHERS ---

        "Adi Shankaracharya", "Ramanujacharya", "Madhvacharya",

        "Swami Vivekananda", "Sri Ramakrishna", "Sri Aurobindo",

        "Kabir", "Mirabai", "Chaitanya Mahaprabhu",

        "Tiruvalluvar", "Basava", 

        "Ramananda", "Nityananda", "Ramakrishna Paramahamsa",



        # --- TEMPLES & SACRED GEOGRAPHY ---

        "Hindu Temples", "Temple Architecture", "Nagara Style", "Dravida Style", "Vesara Style",

        "Kashi Vishwanath Temple", "Somnath Temple", "Tirupati Temple",

        "Jagannath Temple", "Badrinath", "Kedarnath", "Rameswaram",

        "Char Dham", "Sapta Puri",

        "Rivers in Hinduism", "Ganga", "Yamuna", "Saraswati",



        # --- CULTURAL & SYMBOLIC ELEMENTS ---

        "Om", "Tilak", "Bindi", "Rudraksha", "Vibhuti",

        "Vastu Shastra", "Dharma Shastras",

        "Festivals", "Diwali", "Navratri", "Holi", "Janmashtami",

        "Symbolism in Hindu Art", "Hindu Mythological Creatures",



        # --- SPECIALIZED SUBJECTS ---

        "Yoga Sutras of Patanjali", "Brahma Sutras", "Bhagavata Theology",

        "Agni Purana", "Markandeya Purana", "Skanda Purana",

        "Smritis", "Manusmriti", "Yajnavalkya Smriti",

        "Devi Mahatmya", "Rudram", "Sri Suktam",
            
        ]
        
        # --- DEFENSE SYSTEM ---
        self.blocked_keywords = [
            "login", "signup", "register", "cart", "shop", "buy", "pricing", 
            "ads", "click", "subscribe", "facebook", "twitter", "instagram", 
            "tiktok", "linkedin", "pornhub", "casino", "betting", "nsfw", "xxx"
        ]
        
        # STRICT MODE: Only allow high-quality information sources
        self.trusted_domains = [
            "wikipedia.org", ".edu", ".gov", "arxiv.org", "britannica.com", 
            "nature.com", "nasa.gov", "phys.org", "sciencedaily.com", 
            "gutenberg.org", "smithsonianmag.com", "nationalgeographic.com"
        ]
        
        self.subscribe(EVENT_START_LEARNING, self._on_start_learning)
        self.subscribe(EVENT_STOP_LEARNING, self._on_stop_learning)
        self.subscribe(EVENT_GAP_DETECTED, self._on_gap_detected)

    def _on_start_learning(self):
        self._is_learning = True

    def _on_stop_learning(self):
        self._is_learning = False

    def _on_gap_detected(self, topic: str, request_id: str = None):
        # LOGIC FIX: Check visited_topics, not visited_urls
        if topic.lower() in self.visited_topics:
            log.info(f"[{self.name}] Already hunted '{topic}'. Skipping.")
            return 
            
        log.info(f"[{self.name}] Curiosity Triggered! Priority: '{topic}'")
        self.interest_queue.append({'topic': topic, 'req_id': request_id})
        self.visited_topics.add(topic.lower())
        
        if not self._is_learning:
            self._is_learning = True
            self.publish(EVENT_START_LEARNING)

    def _check_db_health(self) -> bool:
        """
        Safety Guard: Checks if DB is getting too big.
        """
        try:
            if os.path.exists(DB_PATH):
                size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
                if size_mb > self.db_limit_mb:
                    log.warning(f"[{self.name}] 🛑 DB Size Limit Reached ({size_mb:.2f}MB). Pausing Learning.")
                    self._is_learning = False
                    self.publish(EVENT_STOP_LEARNING)
                    return False
            return True
        except Exception as e:
            log.error(f"[{self.name}] Health check failed: {e}")
            return True # Assume safe if check fails

    def process_step(self):
        if not self._is_learning: return

        # 1. Safety Check
        if not self._check_db_health(): return

        # 2. Memory Cleanup (Prevent RAM Creep)
        if len(self.visited_urls) > 10000:
            log.info(f"[{self.name}] Clearing visited cache to free RAM.")
            self.visited_urls.clear()

        url_to_scrape = None
        req_id = None
        
        # 3. Priority Hunt
        if self.interest_queue:
            item = self.interest_queue.popleft()
            topic = item['topic']
            req_id = item['req_id']
            log.info(f"[{self.name}] Hunting gap: '{topic}'")
            url_to_scrape = self._search_for_topic(topic, req_id)
        
        # 4. Explore Frontier (Safe Links only)
        elif self.frontier:
            url_to_scrape = self.frontier.popleft()
            if url_to_scrape in self.visited_urls:
                url_to_scrape = None

        # 5. Reset Seed (If stuck)
        if not url_to_scrape and not self.frontier:
             seed = random.choice(self.seeds)
             log.info(f"[{self.name}] Frontier empty. Searching seed: {seed}")
             url_to_scrape = self._search_for_topic(seed, None)

        # Execute
        if url_to_scrape:
            self.visited_urls.add(url_to_scrape)
            self._process_url(url_to_scrape, req_id)
        
        # JITTER: Random sleep to behave like a human
        sleep_time = random.uniform(2.5, 4.5)
        time.sleep(sleep_time)

    def _is_safe_url(self, url: str) -> bool:
        """
        The Bouncer. Strict Mode Enabled.
        """
        url_lower = url.lower()
        
        # 1. Block file types
        if url_lower.endswith(('.pdf', '.jpg', '.png', '.zip', '.exe', '.mp4')): 
            return False
            
        # 2. Block bad keywords
        if any(bad in url_lower for bad in self.blocked_keywords):
            return False
            
        # 3. STRICT MODE: Trusted Domains Only
        # This keeps Turiya in the "Library" and out of the "Dumpster"
        if not any(trust in url_lower for trust in self.trusted_domains):
            # Log occassionally so you know it's working
            # log.debug(f"Blocked untrusted domain: {url}") 
            return False
            
        return True

    def _process_url(self, url: str, req_id: str = None):
        if not self._is_safe_url(url): return

        observations, links = self._scrape_url_and_links(url)
        
        if observations:
            log.info(f"[{self.name}] Extracted {len(observations)} chunks + {len(links)} links from {url}")
            trace_manager.record(req_id, self.name, "Scraping Complete", f"Source: {url}")
            
            for text_chunk in observations:
                if not self._is_learning: break
                self.memory_manager.add_observation(text_chunk, source=url)
                self.publish(EVENT_PERCEPTION_NEW_DATA, source=url)
            
            # Feed Frontier
            for link in links:
                if link not in self.visited_urls and len(self.frontier) < 1000:
                    if self._is_safe_url(link):
                        self.frontier.append(link)

    def _scrape_url_and_links(self, url: str):
        try:
            headers = {'User-Agent': 'SNS2F-Bot/0.1 (Research)'}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code != 200: return [], []

            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Cleanup HTML
            for junk in soup(["script", "style", "nav", "footer", "header", "form", "aside", "iframe"]):
                junk.decompose()

            # Extract Text
            paragraphs = soup.find_all('p')
            cleaned_text = []
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 80: 
                    cleaned_text.append(text)
            
            # Quality Check: Skip thin pages
            if len(cleaned_text) < 3:
                return [], []

            # Extract Links
            new_links = []
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                full_url = urljoin(url, href)
                
                # Basic valid link check
                if full_url.startswith("http"):
                    new_links.append(full_url)
            
            random.shuffle(new_links)
            return cleaned_text[:20], new_links[:5]

        except Exception as e:
            log.error(f"Scraping error: {e}")
            return [], []

    def _search_for_topic(self, topic: str, req_id: str) -> str:
        try:
            # FIX: Removed "OR education" to prevent context bias.
            # Now it just searches for the topic + wikipedia.
            query = f"{topic} wikipedia" 
            
            results = DDGS().text(query, max_results=3)
            
            if results:
                for res in results:
                    url = res.get('href') or res.get('link') or res.get('url')
                    
                    # Extra Safety: If we are looking for "Lord", skip URLs about "persons" if possible
                    # (Simple heuristic to avoid common name collisions)
                    if url and self._is_safe_url(url):
                        log.info(f"[{self.name}] Found source: {url}")
                        trace_manager.record(req_id, self.name, "Web Search Success", url)
                        return url
            
            log.warning(f"[{self.name}] No results found for '{topic}'")
            return None
        except Exception as e:
            log.error(f"[{self.name}] Search failed: {e}")
            return None