"""Idealist searcher - non-profit and social impact jobs."""

import logging
from typing import List
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class IdealistSearcher(BaseJobSearcher):
    """Searcher for Idealist - non-profit and social impact jobs."""

    def __init__(self):
        super().__init__("Idealist")
        self.base_url = "https://www.idealist.org/api/search/jobs"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Idealist for non-profit and social impact jobs."""
        try:
            # Idealist categories:
            # - Advocacy & Human Rights
            # - Animals
            # - Arts & Culture
            # - Community Development
            # - Education
            # - Environment
            # - Health
            # - International Development
            # - Social Services

            issue_area = self._map_keywords_to_issue_area(query.keywords)

            params = {
                "q": " ".join(query.keywords) if query.keywords else "",
                "issueArea": issue_area,
                "location": query.location or "",
                "remote": query.remote_only,
            }

            logger.info(f"Idealist search: {params}")
            return []

        except Exception as e:
            logger.error(f"Error searching Idealist: {e}")
            return []

    def _map_keywords_to_issue_area(self, keywords: List[str]) -> str:
        """Map search keywords to Idealist issue areas."""
        if not keywords:
            return "all"

        keyword_text = " ".join(k.lower() for k in keywords)

        issue_mapping = {
            "advocacy": ["advocacy", "human rights", "policy", "legal", "justice"],
            "animals": ["animal", "wildlife", "veterinary", "conservation"],
            "arts": ["arts", "culture", "museum", "theater", "music"],
            "community": ["community", "housing", "urban", "neighborhood"],
            "education": ["education", "teacher", "tutor", "school", "youth"],
            "environment": ["environment", "climate", "sustainability", "conservation"],
            "health": ["health", "medical", "mental health", "public health"],
            "international": ["international", "global", "humanitarian", "refugee"],
            "social-services": ["social work", "counseling", "case manager", "homeless"],
        }

        for area, terms in issue_mapping.items():
            if any(term in keyword_text for term in terms):
                return area

        return "all"
