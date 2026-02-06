"""Glassdoor job searcher - major job board with company reviews."""

import logging
from typing import List
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class GlassdoorSearcher(BaseJobSearcher):
    """Searcher for Glassdoor - jobs with company insights."""

    def __init__(self):
        super().__init__("Glassdoor")
        self.base_url = "https://api.glassdoor.com/api/api.htm"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Glassdoor for jobs."""
        try:
            # Glassdoor API requires partner credentials
            # Categories: All industries with company reviews
            params = {
                "action": "jobs",
                "q": " ".join(query.keywords) if query.keywords else "",
                "l": query.location or "",
            }

            if query.remote_only:
                params["jobType"] = "remote"

            logger.info(f"Glassdoor search: {params}")
            return []

        except Exception as e:
            logger.error(f"Error searching Glassdoor: {e}")
            return []
