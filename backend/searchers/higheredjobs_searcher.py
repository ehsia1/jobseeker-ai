"""HigherEdJobs searcher - jobs in academia and higher education."""

import logging
from typing import List
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class HigherEdJobsSearcher(BaseJobSearcher):
    """Searcher for HigherEdJobs - academic and higher education jobs."""

    def __init__(self):
        super().__init__("HigherEdJobs")
        self.base_url = "https://www.higheredjobs.com/search/advanced_action.cfm"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search HigherEdJobs for academic positions."""
        try:
            # HigherEdJobs categories:
            # - Faculty
            # - Administrative
            # - Executive
            # - Student Affairs
            # - Academic Affairs
            # - Information Technology
            # - Research
            # - Library
            # - Athletics

            category = self._map_keywords_to_category(query.keywords)

            params = {
                "Keywords": " ".join(query.keywords) if query.keywords else "",
                "Category": category,
                "Location": query.location or "",
                "Remote": "1" if query.remote_only else "0",
            }

            logger.info(f"HigherEdJobs search: {params}")
            return []

        except Exception as e:
            logger.error(f"Error searching HigherEdJobs: {e}")
            return []

    def _map_keywords_to_category(self, keywords: List[str]) -> str:
        """Map search keywords to HigherEdJobs categories."""
        if not keywords:
            return "all"

        keyword_text = " ".join(k.lower() for k in keywords)

        category_mapping = {
            "faculty": ["professor", "faculty", "lecturer", "instructor", "teaching"],
            "administrative": ["administrator", "administrative", "coordinator", "assistant"],
            "executive": ["dean", "provost", "president", "vice president", "director"],
            "student-affairs": ["student affairs", "residence", "housing", "counseling"],
            "academic-affairs": ["academic", "curriculum", "registrar", "advising"],
            "it": ["it", "technology", "developer", "programmer", "systems"],
            "research": ["research", "scientist", "postdoc", "lab"],
            "library": ["library", "librarian", "archivist"],
            "athletics": ["athletic", "coach", "sports", "fitness"],
        }

        for category, terms in category_mapping.items():
            if any(term in keyword_text for term in terms):
                return category

        return "all"
