# sns2f_framework/agents/perception_agent.py

import logging
import time
import random
import requests
from bs4 import BeautifulSoup
from collections import deque
from duckduckgo_search import DDGS
from typing import List, Optional
from sns2f_framework.agents.base_agent import BaseAgent
from sns2f_framework.core.event_bus import (
    EventBus, 
    EVENT_START_LEARNING, 
    EVENT_STOP_LEARNING, 
    EVENT_PERCEPTION_NEW_DATA,
    EVENT_GAP_DETECTED # <--- New Event
)
from sns2f_framework.memory.memory_manager import MemoryManager
from sns2f_framework.config import WHITELISTED_SOURCES

log = logging.getLogger(__name__)

class PerceptionAgent(BaseAgent):
    """
    The 'Eyes' of the swarm.
    V3 Upgrade: Curiosity-Driven.
    It prioritizes searching for 'Knowledge Gaps' over random reading.
    """

    def __init__(self, name: str, event_bus: EventBus, memory_manager: MemoryManager):
        super().__init__(name, event_bus)
        self.memory_manager = memory_manager
        self._is_learning = False
        
        # Priority Queue for things we are curious about
        self.interest_queue = deque()
        
        self.subscribe(EVENT_START_LEARNING, self._on_start_learning)
        self.subscribe(EVENT_STOP_LEARNING, self._on_stop_learning)
        self.subscribe(EVENT_GAP_DETECTED, self._on_gap_detected)

    def _on_start_learning(self):
        log.info(f"[{self.name}] Engaging sensors.")
        self._is_learning = True

    def _on_stop_learning(self):
        log.info(f"[{self.name}] Idling.")
        self._is_learning = False

    def _on_gap_detected(self, topic: str):
        """
        Triggered when the Brain is confused.
        We add this topic to our high-priority search list.
        """
        log.info(f"[{self.name}] Curiosity Triggered! Added '{topic}' to interest queue.")
        self.interest_queue.append(topic)
        
        # If we aren't learning, we auto-start briefly to satisfy curiosity
        if not self._is_learning:
            log.info(f"[{self.name}] Auto-waking to investigate gap...")
            self._is_learning = True
            # We will naturally go back to sleep via main loop logic if needed,
            # or user can stop. For now, we just wake up.

    def process_step(self):
        if not self._is_learning:
            return

        url_to_scrape = None
        
        # 1. Check Priority Queue (Curiosity)
        if self.interest_queue:
            topic = self.interest_queue.popleft()
            log.info(f"[{self.name}] Hunting info for gap: '{topic}'")
            url_to_scrape = self._search_for_topic(topic)
        
        # 2. If no priority, pick Random (Exploration)
        if not url_to_scrape:
             # Only explore randomly if the queue was empty
             url_to_scrape = self._pick_random_source()
             log.info(f"[{self.name}] Exploring random source: {url_to_scrape}")

        # 3. Scrape
        if url_to_scrape:
            self._process_url(url_to_scrape)
        
        # Sleep to be polite
        time.sleep(3.0)

    def _search_for_topic(self, topic: str) -> str:
        """
        Uses DuckDuckGo to find a Wikipedia article for the topic.
        """
        try:
            # We specifically look for wikipedia to keep quality high for now
            query = f"{topic} site:en.wikipedia.org"
            results = DDGS().text(query, max_results=1)
            if results:
                found_url = results[0]['href']
                log.info(f"[{self.name}] Found source for '{topic}': {found_url}")
                return found_url
            else:
                log.warning(f"[{self.name}] No results found for '{topic}'")
                return None
        except Exception as e:
            log.error(f"[{self.name}] Search failed: {e}")
            return None

    def _pick_random_source(self) -> str:
        if not WHITELISTED_SOURCES:
            return "https://en.wikipedia.org/wiki/Artificial_intelligence"
        return random.choice(WHITELISTED_SOURCES)

    def _process_url(self, url: str):
        observations = self._scrape_url(url)
        if observations:
            log.info(f"[{self.name}] Extracted {len(observations)} chunks.")
            for text_chunk in observations:
                if not self._is_learning: break
                self.memory_manager.add_observation(text_chunk, source=url)
                self.publish(EVENT_PERCEPTION_NEW_DATA, source=url)
                time.sleep(0.5)

    def _scrape_url(self, url: str) -> List[str]:
        try:
            headers = {'User-Agent': 'SNS2F-Bot/0.1 (Internal Research)'}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code != 200: return []

            soup = BeautifulSoup(response.content, 'html.parser')
            paragraphs = soup.find_all('p')
            
            cleaned = []
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 60: cleaned.append(text)
            
            # Deep read (20 paragraphs)
            return cleaned[:20]

        except Exception as e:
            log.error(f"Scraping error: {e}")
            return []