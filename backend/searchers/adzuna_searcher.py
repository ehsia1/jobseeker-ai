"""Adzuna job aggregator searcher - best Indeed alternative with global coverage."""

import aiohttp
import logging
import os
from typing import List, Optional
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class AdzunaSearcher(BaseJobSearcher):
    """
    Searcher for Adzuna - major job aggregator covering 16+ countries.

    Adzuna aggregates jobs from thousands of sources and provides
    a free API with 250 calls/day on the free tier.

    API docs: https://developer.adzuna.com/
    """

    # Supported countries and their API endpoints
    COUNTRIES = {
        "us": "api.adzuna.com",
        "gb": "api.adzuna.com",
        "au": "api.adzuna.com",
        "ca": "api.adzuna.com",
        "de": "api.adzuna.com",
        "fr": "api.adzuna.com",
        "in": "api.adzuna.com",
        "nl": "api.adzuna.com",
        "nz": "api.adzuna.com",
        "pl": "api.adzuna.com",
        "za": "api.adzuna.com",
        "br": "api.adzuna.com",
        "at": "api.adzuna.com",
        "ch": "api.adzuna.com",
        "it": "api.adzuna.com",
        "sg": "api.adzuna.com",
    }

    def __init__(self):
        super().__init__("Adzuna")
        self.app_id = os.getenv("ADZUNA_APP_ID", "")
        self.app_key = os.getenv("ADZUNA_APP_KEY", "")
        self.default_country = os.getenv("ADZUNA_COUNTRY", "us")

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Adzuna for jobs across multiple sources."""
        results = []

        # Check for API credentials
        if not self.app_id or not self.app_key:
            logger.warning("Adzuna API credentials not configured. Set ADZUNA_APP_ID and ADZUNA_APP_KEY environment variables.")
            return []

        try:
            # Build search query
            what = " ".join(query.keywords) if query.keywords else ""
            where = query.location or ""

            # Determine country from location
            country = self._detect_country(where)

            params = {
                "app_id": self.app_id,
                "app_key": self.app_key,
                "results_per_page": min(query.limit, 50),
                "what": what,
                "content-type": "application/json",
            }

            if where:
                params["where"] = where

            if query.remote_only:
                # Add remote to search terms
                params["what"] = f"{what} remote".strip()

            if query.min_rate:
                params["salary_min"] = query.min_rate

            if query.max_rate:
                params["salary_max"] = query.max_rate

            url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"

            logger.info(f"Adzuna search: country={country}, what={params.get('what')}")

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 401:
                        logger.error("Adzuna API authentication failed - check credentials")
                        return []
                    if response.status == 429:
                        logger.warning("Adzuna API rate limit reached")
                        return []
                    if response.status != 200:
                        logger.warning(f"Adzuna API returned {response.status}")
                        return []

                    data = await response.json()

            jobs = data.get("results", [])

            for job in jobs:
                result = self._parse_job(job)
                if result:
                    results.append(result)

            logger.info(f"Found {len(results)} jobs on Adzuna")

        except Exception as e:
            logger.error(f"Error searching Adzuna: {e}")

        return results

    def _parse_job(self, job: dict) -> Optional[SearchResult]:
        """Parse an Adzuna job listing."""
        try:
            title = job.get("title", "")
            if not title:
                return None

            company = job.get("company", {})
            company_name = company.get("display_name") if isinstance(company, dict) else str(company)

            location = job.get("location", {})
            if isinstance(location, dict):
                location_parts = location.get("display_name", "").split(", ")
                location_str = ", ".join(location_parts[:2]) if location_parts else ""
            else:
                location_str = str(location)

            description = job.get("description", "")

            # Parse salary
            salary_min = job.get("salary_min")
            salary_max = job.get("salary_max")
            salary_type = "annual" if salary_min or salary_max else None

            # Parse date
            posted_date = None
            created = job.get("created")
            if created:
                try:
                    posted_date = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except Exception:
                    pass

            # Check if remote
            remote = "remote" in (title + description).lower()

            # Extract skills
            skills = self.extract_skills(description)

            return SearchResult(
                source=self.source_name,
                source_id=job.get("id"),
                title=title,
                company=company_name,
                description=description[:2000],
                url=job.get("redirect_url", ""),
                location=location_str,
                remote=remote,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_type=salary_type,
                skills=skills[:20],
                posted_date=posted_date,
                job_type=job.get("contract_type"),
                experience_level=None,
                raw_data=job
            )

        except Exception as e:
            logger.error(f"Error parsing Adzuna job: {e}")
            return None

    def _detect_country(self, location: str) -> str:
        """Detect country code from location string."""
        if not location:
            return self.default_country

        location_lower = location.lower()

        # Common country patterns
        country_patterns = {
            "us": ["united states", "usa", "u.s.", "america", "new york", "san francisco", "los angeles", "chicago", "seattle", "boston", "austin", "denver"],
            "gb": ["united kingdom", "uk", "england", "london", "manchester", "birmingham", "scotland", "wales"],
            "ca": ["canada", "toronto", "vancouver", "montreal", "ottawa", "calgary"],
            "au": ["australia", "sydney", "melbourne", "brisbane", "perth"],
            "de": ["germany", "deutschland", "berlin", "munich", "frankfurt", "hamburg"],
            "fr": ["france", "paris", "lyon", "marseille"],
            "in": ["india", "bangalore", "mumbai", "delhi", "hyderabad", "chennai", "pune"],
            "nl": ["netherlands", "amsterdam", "rotterdam", "utrecht"],
            "nz": ["new zealand", "auckland", "wellington"],
            "sg": ["singapore"],
        }

        for country_code, patterns in country_patterns.items():
            if any(p in location_lower for p in patterns):
                return country_code

        return self.default_country
