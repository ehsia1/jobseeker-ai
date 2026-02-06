"""Working Nomads job searcher - remote jobs for digital nomads."""

import aiohttp
import logging
import re
from typing import List, Optional
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class WorkingNomadsSearcher(BaseJobSearcher):
    """Searcher for Working Nomads - remote jobs worldwide via public API."""

    BASE_URL = "https://www.workingnomads.com/api/exposed_jobs/"

    # Category slugs used by Working Nomads
    CATEGORIES = {
        "development": ["developer", "engineer", "programming", "software", "backend", "frontend", "python", "javascript", "react", "node"],
        "design": ["design", "ux", "ui", "graphic", "creative", "figma"],
        "devops-sysadmin": ["devops", "sre", "infrastructure", "cloud", "kubernetes", "aws", "docker"],
        "marketing": ["marketing", "seo", "content", "growth", "social media"],
        "sales": ["sales", "business development", "account executive"],
        "writing": ["writer", "editor", "copywriter", "content writer"],
        "data-science": ["data", "analytics", "machine learning", "ai", "ml", "scientist"],
        "management-finance": ["manager", "director", "finance", "accounting", "lead"],
        "customer-success": ["support", "customer service", "help desk", "customer success"],
        "education": ["teacher", "tutor", "education", "instructor", "training"],
        "legal": ["legal", "lawyer", "paralegal", "attorney", "compliance"],
        "human-resources": ["hr", "recruiting", "talent", "people ops", "recruiter"],
    }

    def __init__(self):
        super().__init__("WorkingNomads")

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Working Nomads for remote jobs via public API."""
        results = []

        try:
            logger.info(f"WorkingNomads fetching jobs from API")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"WorkingNomads API returned {response.status}")
                        return []

                    jobs = await response.json()

            # Filter by category if keywords provided
            target_category = self._map_keywords_to_category(query.keywords)

            for job in jobs:
                # Category filter
                job_category = job.get("category_name", "").lower().replace(" ", "-")
                if target_category and target_category != "all":
                    if target_category not in job_category and job_category not in target_category:
                        # Also check if keywords match the job
                        if not self._matches_keywords(job, query.keywords):
                            continue

                result = self._parse_job(job)
                if result:
                    # Final keyword filter
                    if self._matches_keywords_result(result, query.keywords):
                        results.append(result)
                        if len(results) >= query.limit:
                            break

            logger.info(f"Found {len(results)} jobs on WorkingNomads")

        except Exception as e:
            logger.error(f"Error searching WorkingNomads: {e}")

        return results

    def _parse_job(self, job: dict) -> Optional[SearchResult]:
        """Parse a Working Nomads job listing."""
        try:
            title = job.get("title", "")
            if not title:
                return None

            company = job.get("company_name", "")
            description = job.get("description", "")

            # Clean HTML from description
            description = re.sub(r'<[^>]+>', ' ', description)
            description = re.sub(r'\s+', ' ', description).strip()

            # Parse location
            location = job.get("location", "Remote")
            if not location:
                location = "Remote / Worldwide"

            # Parse date
            posted_date = None
            pub_date = job.get("pub_date")
            if pub_date:
                try:
                    posted_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                except Exception:
                    pass

            # Extract skills from tags and description
            skills = []
            tags = job.get("tags", "")
            if tags:
                skills = [t.strip() for t in tags.split(",") if t.strip()]

            # Also extract from description
            desc_skills = self.extract_skills(description)
            skills.extend(desc_skills)
            skills = list(set(skills))[:20]

            # Parse salary if in description
            salary_min, salary_max, salary_type = self.parse_salary(description)

            return SearchResult(
                source=self.source_name,
                source_id=job.get("url", ""),  # Use URL as unique ID
                title=title,
                company=company,
                description=description[:2000],
                url=job.get("url", ""),
                location=location,
                remote=True,  # All Working Nomads jobs are remote
                salary_min=salary_min,
                salary_max=salary_max,
                salary_type=salary_type,
                skills=skills,
                posted_date=posted_date,
                job_type=None,
                experience_level=None,
                raw_data=job
            )

        except Exception as e:
            logger.error(f"Error parsing WorkingNomads job: {e}")
            return None

    def _matches_keywords(self, job: dict, keywords: Optional[List[str]]) -> bool:
        """Check if job matches any of the keywords."""
        if not keywords:
            return True

        text = f"{job.get('title', '')} {job.get('description', '')} {job.get('company_name', '')} {job.get('tags', '')}".lower()
        return any(kw.lower() in text for kw in keywords)

    def _matches_keywords_result(self, result: SearchResult, keywords: Optional[List[str]]) -> bool:
        """Check if result matches any of the keywords."""
        if not keywords:
            return True

        text = f"{result.title} {result.description} {result.company or ''}".lower()
        return any(kw.lower() in text for kw in keywords)

    def _map_keywords_to_category(self, keywords: Optional[List[str]]) -> Optional[str]:
        """Map search keywords to Working Nomads categories."""
        if not keywords:
            return None

        keyword_text = " ".join(k.lower() for k in keywords)

        for category, terms in self.CATEGORIES.items():
            if any(term in keyword_text for term in terms):
                return category

        return None
