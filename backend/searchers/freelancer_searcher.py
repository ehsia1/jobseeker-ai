"""Freelancer.com searcher - global freelance marketplace."""

import logging
from typing import List
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class FreelancerSearcher(BaseJobSearcher):
    """Searcher for Freelancer.com - global freelance project marketplace."""

    def __init__(self):
        super().__init__("Freelancer")
        # Freelancer has a public API
        self.base_url = "https://www.freelancer.com/api/projects/0.1/projects/active"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Freelancer.com for freelance projects."""
        try:
            # Freelancer job categories:
            # - Websites, IT & Software
            # - Mobile Phones & Computing
            # - Writing & Content
            # - Design, Media & Architecture
            # - Data Entry & Admin
            # - Engineering & Science
            # - Sales & Marketing
            # - Translation & Languages
            # - Finance & Management

            category = self._map_keywords_to_category(query.keywords)

            params = {
                "query": " ".join(query.keywords) if query.keywords else "",
                "job_details": True,
                "compact": False,
                "jobs[]": category,
            }

            logger.info(f"Freelancer search: {params}")
            return []

        except Exception as e:
            logger.error(f"Error searching Freelancer: {e}")
            return []

    def _map_keywords_to_category(self, keywords: List[str]) -> str:
        """Map search keywords to Freelancer categories."""
        if not keywords:
            return "all"

        keyword_text = " ".join(k.lower() for k in keywords)

        category_mapping = {
            "websites-it-software": ["web", "software", "developer", "programming", "python", "javascript"],
            "mobile": ["mobile", "android", "ios", "app", "flutter", "react native"],
            "writing": ["writing", "content", "copywriting", "article", "blog"],
            "design": ["design", "graphic", "logo", "photoshop", "illustrator"],
            "data-entry": ["data entry", "admin", "virtual assistant", "excel"],
            "engineering": ["engineering", "cad", "mechanical", "electrical", "3d modeling"],
            "sales-marketing": ["marketing", "seo", "sales", "social media", "advertising"],
            "translation": ["translation", "transcription", "language", "localization"],
            "finance": ["accounting", "finance", "bookkeeping", "financial analysis"],
        }

        for category, terms in category_mapping.items():
            if any(term in keyword_text for term in terms):
                return category

        return "all"
