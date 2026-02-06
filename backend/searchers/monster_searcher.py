"""Monster job searcher - classic job board for all industries."""

import logging
from typing import List
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class MonsterSearcher(BaseJobSearcher):
    """Searcher for Monster - established job board for all professions."""

    def __init__(self):
        super().__init__("Monster")
        self.base_url = "https://api.monster.com/jobs/v2"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Monster for jobs."""
        try:
            # Monster API requires authentication
            params = {
                "q": " ".join(query.keywords) if query.keywords else "",
                "where": query.location or "",
                "page": 1,
                "pageSize": query.limit or 25,
            }

            logger.info(f"Monster search: {params}")
            return []

        except Exception as e:
            logger.error(f"Error searching Monster: {e}")
            return []
