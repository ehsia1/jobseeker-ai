"""Behance Jobs searcher - creative jobs from Adobe's creative network."""

import logging
from typing import List
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class BehanceSearcher(BaseJobSearcher):
    """Searcher for Behance Jobs - creative jobs from Adobe's network."""

    def __init__(self):
        super().__init__("Behance")
        self.base_url = "https://www.behance.net/joblist"

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Behance for creative jobs."""
        try:
            # Behance job categories:
            # - Animation
            # - Branding
            # - Fashion
            # - Graphic Design
            # - Illustration
            # - Industrial Design
            # - Interaction Design
            # - Motion Graphics
            # - Photography
            # - UI/UX Design
            # - Web Design

            field = self._map_keywords_to_field(query.keywords)

            params = {
                "search": " ".join(query.keywords) if query.keywords else "",
                "field": field,
                "location": query.location or "",
            }

            if query.remote_only:
                params["remote"] = "true"

            logger.info(f"Behance search: {params}")
            return []

        except Exception as e:
            logger.error(f"Error searching Behance: {e}")
            return []

    def _map_keywords_to_field(self, keywords: List[str]) -> str:
        """Map search keywords to Behance creative fields."""
        if not keywords:
            return "all"

        keyword_text = " ".join(k.lower() for k in keywords)

        field_mapping = {
            "animation": ["animation", "animator", "motion", "after effects"],
            "branding": ["branding", "brand", "identity", "logo"],
            "fashion": ["fashion", "apparel", "clothing", "textile"],
            "graphic-design": ["graphic design", "print", "layout", "typography"],
            "illustration": ["illustration", "illustrator", "drawing"],
            "industrial-design": ["industrial design", "product design", "3d"],
            "interaction-design": ["interaction", "ux", "user experience"],
            "motion-graphics": ["motion graphics", "video", "vfx"],
            "photography": ["photography", "photographer", "photo"],
            "ui-ux": ["ui", "ux", "user interface", "figma", "sketch"],
            "web-design": ["web design", "website", "frontend", "css"],
        }

        for field, terms in field_mapping.items():
            if any(term in keyword_text for term in terms):
                return field

        return "all"
