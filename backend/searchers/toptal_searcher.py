"""Toptal searcher - premium freelance network for top talent."""

import logging
from typing import List
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class ToptalSearcher(BaseJobSearcher):
    """Searcher for Toptal - premium freelance network for top 3% talent."""

    def __init__(self):
        super().__init__("Toptal")
        self.base_url = "https://www.toptal.com/developers/jobs"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Toptal for premium freelance opportunities."""
        try:
            # Toptal specializations:
            # - Software Developers
            # - Designers
            # - Finance Experts
            # - Project Managers
            # - Product Managers
            # - Data Scientists
            # - DevOps Engineers

            specialization = self._map_keywords_to_specialization(query.keywords)

            params = {
                "query": " ".join(query.keywords) if query.keywords else "",
                "specialization": specialization,
            }

            logger.info(f"Toptal search: {params}")
            return []

        except Exception as e:
            logger.error(f"Error searching Toptal: {e}")
            return []

    def _map_keywords_to_specialization(self, keywords: List[str]) -> str:
        """Map search keywords to Toptal specializations."""
        if not keywords:
            return "all"

        keyword_text = " ".join(k.lower() for k in keywords)

        specialization_mapping = {
            "developers": ["developer", "engineer", "software", "programming", "backend", "frontend", "fullstack"],
            "designers": ["designer", "ux", "ui", "graphic", "product design"],
            "finance": ["finance", "accounting", "cfo", "financial modeling", "valuation"],
            "project-managers": ["project manager", "scrum master", "agile"],
            "product-managers": ["product manager", "product owner", "pm"],
            "data-scientists": ["data scientist", "machine learning", "ai", "analytics"],
            "devops": ["devops", "sre", "infrastructure", "cloud", "kubernetes"],
        }

        for spec, terms in specialization_mapping.items():
            if any(term in keyword_text for term in terms):
                return spec

        return "all"
