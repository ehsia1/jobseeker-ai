"""SimplyHired job searcher - job aggregator for all industries."""

import logging
from typing import List
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class SimplyHiredSearcher(BaseJobSearcher):
    """Searcher for SimplyHired - job aggregator across industries."""

    def __init__(self):
        super().__init__("SimplyHired")
        self.base_url = "https://www.simplyhired.com/api/jobs"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search SimplyHired for jobs."""
        try:
            params = {
                "q": " ".join(query.keywords) if query.keywords else "",
                "l": query.location or "",
                "pn": 1,
            }

            if query.remote_only:
                params["fjt"] = "remote"

            logger.info(f"SimplyHired search: {params}")
            return []

        except Exception as e:
            logger.error(f"Error searching SimplyHired: {e}")
            return []
