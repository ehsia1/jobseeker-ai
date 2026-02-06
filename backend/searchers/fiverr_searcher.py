"""Fiverr searcher - gig marketplace for freelance services."""

import logging
from typing import List
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class FiverrSearcher(BaseJobSearcher):
    """Searcher for Fiverr - freelance gig marketplace."""

    def __init__(self):
        super().__init__("Fiverr")
        self.base_url = "https://www.fiverr.com/search/gigs"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Fiverr for freelance gigs/buyer requests."""
        try:
            # Fiverr categories:
            # - Graphics & Design
            # - Digital Marketing
            # - Writing & Translation
            # - Video & Animation
            # - Music & Audio
            # - Programming & Tech
            # - Business
            # - Data
            # - AI Services

            category = self._map_keywords_to_category(query.keywords)

            params = {
                "query": " ".join(query.keywords) if query.keywords else "",
                "category": category,
            }

            logger.info(f"Fiverr search: {params}")
            return []

        except Exception as e:
            logger.error(f"Error searching Fiverr: {e}")
            return []

    def _map_keywords_to_category(self, keywords: List[str]) -> str:
        """Map search keywords to Fiverr categories."""
        if not keywords:
            return "all"

        keyword_text = " ".join(k.lower() for k in keywords)

        category_mapping = {
            "graphics-design": ["design", "logo", "graphic", "illustration", "branding"],
            "digital-marketing": ["marketing", "seo", "social media", "advertising"],
            "writing-translation": ["writing", "copywriting", "translation", "content"],
            "video-animation": ["video", "animation", "editing", "motion graphics"],
            "music-audio": ["music", "audio", "voice", "podcast", "sound"],
            "programming-tech": ["programming", "developer", "web", "app", "software"],
            "business": ["business", "consulting", "virtual assistant", "data entry"],
            "data": ["data", "analytics", "database", "excel", "visualization"],
            "ai-services": ["ai", "machine learning", "chatbot", "automation"],
        }

        for category, terms in category_mapping.items():
            if any(term in keyword_text for term in terms):
                return category

        return "all"
