"""Mediabistro searcher - media, marketing, and communications jobs."""

import logging
from typing import List
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class MediabistroSearcher(BaseJobSearcher):
    """Searcher for Mediabistro - media, marketing, and communications jobs."""

    def __init__(self):
        super().__init__("Mediabistro")
        self.base_url = "https://www.mediabistro.com/jobs/search"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Mediabistro for media and communications jobs."""
        try:
            # Mediabistro categories:
            # - Advertising
            # - Communications
            # - Content
            # - Design
            # - Digital Media
            # - Editorial
            # - Marketing
            # - PR
            # - Social Media
            # - Video/Film

            category = self._map_keywords_to_category(query.keywords)

            params = {
                "q": " ".join(query.keywords) if query.keywords else "",
                "category": category,
                "location": query.location or "",
            }

            if query.remote_only:
                params["remote"] = "true"

            logger.info(f"Mediabistro search: {params}")
            return []

        except Exception as e:
            logger.error(f"Error searching Mediabistro: {e}")
            return []

    def _map_keywords_to_category(self, keywords: List[str]) -> str:
        """Map search keywords to Mediabistro categories."""
        if not keywords:
            return "all"

        keyword_text = " ".join(k.lower() for k in keywords)

        category_mapping = {
            "advertising": ["advertising", "ad agency", "creative director"],
            "communications": ["communications", "internal comms", "corporate"],
            "content": ["content", "content strategy", "content marketing"],
            "design": ["design", "graphic design", "art director"],
            "digital": ["digital", "web", "online", "social media manager"],
            "editorial": ["editor", "editorial", "writer", "journalist"],
            "marketing": ["marketing", "brand", "campaign"],
            "pr": ["pr", "public relations", "publicity", "media relations"],
            "social-media": ["social media", "community manager", "influencer"],
            "video": ["video", "film", "producer", "videographer"],
        }

        for category, terms in category_mapping.items():
            if any(term in keyword_text for term in terms):
                return category

        return "all"
