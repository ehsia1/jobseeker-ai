"""Remotive job searcher - free public API for remote tech jobs."""

import aiohttp
import logging
from typing import List, Optional
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class RemotiveSearcher(BaseJobSearcher):
    """
    Searcher for Remotive.io - free public API for remote jobs.

    Remotive has a free public API with no authentication required.
    API docs: https://remotive.io/api-documentation
    """

    BASE_URL = "https://remotive.io/api/remote-jobs"

    # Available categories from the API
    CATEGORIES = {
        "software-dev": ["software", "developer", "engineer", "programming", "python", "javascript", "react", "node", "backend", "frontend"],
        "customer-support": ["support", "customer service", "help desk", "success"],
        "design": ["design", "ux", "ui", "graphic", "creative", "figma"],
        "marketing": ["marketing", "seo", "content", "growth", "social media"],
        "sales": ["sales", "business development", "account executive"],
        "product": ["product manager", "product owner", "pm"],
        "finance-legal": ["finance", "accounting", "legal", "cfo"],
        "hr": ["hr", "recruiting", "talent", "people", "recruiter"],
        "data": ["data", "analytics", "machine learning", "ai", "ml", "scientist"],
        "devops-sysadmin": ["devops", "sysadmin", "infrastructure", "cloud", "aws", "kubernetes"],
        "writing": ["writer", "copywriter", "content writer", "editor", "copywriting"],
        "qa": ["qa", "quality", "testing", "test engineer"],
        "project-management": ["project manager", "scrum", "agile", "pmo"],
        "all-others": [],  # Default fallback
    }

    def __init__(self):
        super().__init__("Remotive")

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Remotive for remote tech jobs."""
        results = []

        try:
            # Build params
            params = {
                "limit": min(query.limit * 2, 100),  # Get extra for filtering
            }

            # Map keywords to category
            category = self._map_keywords_to_category(query.keywords)
            if category and category != "all-others":
                params["category"] = category

            # Add search term if keywords provided
            if query.keywords:
                params["search"] = " ".join(query.keywords)

            logger.info(f"Remotive search: category={category}, search={params.get('search')}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Remotive API returned {response.status}")
                        return []

                    data = await response.json()

            jobs = data.get("jobs", [])

            for job in jobs:
                result = self._parse_job(job)
                if result:
                    # Additional keyword filtering
                    if self._matches_keywords(result, query.keywords):
                        results.append(result)
                        if len(results) >= query.limit:
                            break

            logger.info(f"Found {len(results)} jobs on Remotive")

        except Exception as e:
            logger.error(f"Error searching Remotive: {e}")

        return results

    def _parse_job(self, job: dict) -> Optional[SearchResult]:
        """Parse a Remotive job listing."""
        try:
            title = job.get("title", "")
            if not title:
                return None

            company = job.get("company_name", "")
            description = job.get("description", "")

            # Parse location
            candidate_location = job.get("candidate_required_location", "")
            location = candidate_location if candidate_location else "Worldwide"

            # Parse salary
            salary_text = job.get("salary", "")
            salary_min, salary_max, salary_type = None, None, None
            if salary_text:
                salary_min, salary_max, salary_type = self.parse_salary(salary_text)

            # Parse date
            posted_date = None
            pub_date = job.get("publication_date")
            if pub_date:
                try:
                    posted_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                except Exception:
                    pass

            # Extract skills from description
            skills = self.extract_skills(description)

            # Add tags as skills too
            tags = job.get("tags", [])
            if tags:
                skills.extend(tags)
                skills = list(set(skills))

            return SearchResult(
                source=self.source_name,
                source_id=str(job.get("id", "")),
                title=title,
                company=company,
                description=description[:2000],
                url=job.get("url", ""),
                location=location,
                remote=True,  # All Remotive jobs are remote
                salary_min=salary_min,
                salary_max=salary_max,
                salary_type=salary_type,
                skills=skills[:20],
                posted_date=posted_date,
                job_type=job.get("job_type"),
                experience_level=None,
                raw_data=job
            )

        except Exception as e:
            logger.error(f"Error parsing Remotive job: {e}")
            return None

    def _matches_keywords(self, result: SearchResult, keywords: Optional[List[str]]) -> bool:
        """Check if result matches any of the keywords."""
        if not keywords:
            return True

        text = f"{result.title} {result.description} {result.company or ''}".lower()
        return any(kw.lower() in text for kw in keywords)

    def _map_keywords_to_category(self, keywords: Optional[List[str]]) -> Optional[str]:
        """Map search keywords to Remotive categories."""
        if not keywords:
            return None

        keyword_text = " ".join(k.lower() for k in keywords)

        for category, terms in self.CATEGORIES.items():
            if any(term in keyword_text for term in terms):
                return category

        return None
