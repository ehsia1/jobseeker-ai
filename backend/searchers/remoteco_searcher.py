"""Remote.co job searcher - curated remote job listings."""

import logging
from typing import List
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class RemoteCoSearcher(BaseJobSearcher):
    """Searcher for Remote.co - curated remote job listings."""

    def __init__(self):
        super().__init__("RemoteCo")
        self.base_url = "https://remote.co/remote-jobs"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Remote.co for remote jobs."""
        try:
            # Remote.co categories:
            # - Accounting
            # - Customer Service
            # - Data Entry
            # - Design
            # - Developer
            # - Editing
            # - HR
            # - Legal
            # - Marketing
            # - Medical & Health
            # - Project Management
            # - QA
            # - Sales
            # - Teaching
            # - Virtual Assistant
            # - Writing

            category = self._map_keywords_to_category(query.keywords)

            params = {
                "category": category,
            }

            logger.info(f"Remote.co search: {params}")
            return []

        except Exception as e:
            logger.error(f"Error searching Remote.co: {e}")
            return []

    def _map_keywords_to_category(self, keywords: List[str]) -> str:
        """Map search keywords to Remote.co categories."""
        if not keywords:
            return "all"

        keyword_text = " ".join(k.lower() for k in keywords)

        category_mapping = {
            "accounting": ["accounting", "finance", "bookkeeping", "cpa"],
            "customer-service": ["customer service", "support", "help desk"],
            "design": ["design", "ux", "ui", "graphic"],
            "developer": ["developer", "engineer", "programming", "software", "python", "javascript"],
            "hr": ["hr", "human resources", "recruiting", "talent"],
            "legal": ["legal", "lawyer", "paralegal", "attorney"],
            "marketing": ["marketing", "seo", "content", "social media"],
            "medical-health": ["medical", "health", "nurse", "healthcare"],
            "project-management": ["project manager", "scrum", "agile"],
            "sales": ["sales", "business development"],
            "teaching": ["teacher", "tutor", "education", "instructor"],
            "writing": ["writer", "copywriter", "content writer", "editor"],
        }

        for category, terms in category_mapping.items():
            if any(term in keyword_text for term in terms):
                return category

        return "all"
