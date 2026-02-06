"""ZipRecruiter job searcher - large job aggregator."""

import logging
from typing import List
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class ZipRecruiterSearcher(BaseJobSearcher):
    """Searcher for ZipRecruiter - job aggregator for all industries."""

    def __init__(self):
        super().__init__("ZipRecruiter")
        self.base_url = "https://api.ziprecruiter.com/jobs/v1"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search ZipRecruiter for jobs."""
        try:
            # ZipRecruiter API requires API key
            params = {
                "search": " ".join(query.keywords) if query.keywords else "",
                "location": query.location or "",
                "jobs_per_page": query.limit or 25,
            }

            if query.remote_only:
                params["remote"] = "1"

            logger.info(f"ZipRecruiter search: {params}")
            return []

        except Exception as e:
            logger.error(f"Error searching ZipRecruiter: {e}")
            return []
