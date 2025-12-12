"""Dribbble job board searcher for design professionals."""

import aiohttp
import logging
from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class DribbbleSearcher(BaseJobSearcher):
    """Searcher for Dribbble jobs - specialized in design roles."""

    BASE_URL = "https://dribbble.com/jobs"

    DESIGN_SKILLS = [
        "figma", "sketch", "adobe xd", "photoshop", "illustrator",
        "indesign", "after effects", "motion design", "ui design",
        "ux design", "user research", "prototyping", "wireframing",
        "design systems", "typography", "branding", "illustration",
        "3d design", "blender", "cinema 4d", "framer", "principle"
    ]

    def __init__(self):
        super().__init__("dribbble")

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Dribbble for design jobs."""
        results = []

        try:
            params = {}
            if query.keywords:
                params["q"] = " ".join(query.keywords)
            if query.remote_only:
                params["anywhere"] = "true"
            if query.location:
                params["location"] = query.location

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL, params=params, headers=headers
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Dribbble returned {response.status}")
                        return results

                    html = await response.text()
                    results = self._parse_html(html, query.limit)

        except Exception as e:
            logger.error(f"Dribbble search error: {e}")

        return results

    def _parse_html(self, html: str, limit: int) -> List[SearchResult]:
        """Parse Dribbble job listings from HTML."""
        results = []
        soup = BeautifulSoup(html, "html.parser")

        job_cards = soup.select(".job-listing, .job, [data-job-id]")

        for card in job_cards[:limit]:
            try:
                result = self._parse_job_card(card)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Error parsing Dribbble job card: {e}")
                continue

        return results

    def _parse_job_card(self, card) -> Optional[SearchResult]:
        """Parse a single job card."""
        title_elem = card.select_one(".job-title, h3, h2")
        title = title_elem.get_text(strip=True) if title_elem else ""
        if not title:
            return None

        company_elem = card.select_one(".company-name, .employer")
        company = company_elem.get_text(strip=True) if company_elem else None

        location_elem = card.select_one(".location, .job-location")
        location = location_elem.get_text(strip=True) if location_elem else None

        desc_elem = card.select_one(".job-description, .description, p")
        description = desc_elem.get_text(strip=True) if desc_elem else title

        link_elem = card.select_one("a[href*='/jobs/']")
        url = ""
        source_id = None
        if link_elem and link_elem.get("href"):
            href = link_elem["href"]
            if not href.startswith("http"):
                href = f"https://dribbble.com{href}"
            url = href
            source_id = href.split("/")[-1] if "/" in href else None

        remote = False
        if location:
            remote = any(
                kw in location.lower()
                for kw in ["remote", "anywhere", "worldwide"]
            )

        return SearchResult(
            source="dribbble",
            source_id=source_id,
            title=title,
            company=company,
            description=description,
            url=url,
            location=location,
            remote=remote,
            skills=self._extract_design_skills(description + " " + title),
            job_type="full-time",
            raw_data={"html": str(card)[:500]},
        )

    def _extract_design_skills(self, text: str) -> List[str]:
        """Extract design-specific skills."""
        text_lower = text.lower()
        found = []

        for skill in self.DESIGN_SKILLS:
            if skill in text_lower:
                found.append(skill.title())

        # Also check general skills
        found.extend(self.extract_skills(text))

        return list(set(found))[:15]
