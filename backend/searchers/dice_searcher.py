"""Dice job board searcher for technology professionals."""

import aiohttp
import logging
from typing import List, Optional
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class DiceSearcher(BaseJobSearcher):
    """Searcher for Dice.com - specialized in tech jobs."""

    BASE_URL = "https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/search"

    def __init__(self):
        super().__init__("dice")

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Dice for tech jobs."""
        results = []

        try:
            params = {
                "q": " ".join(query.keywords or ["software"]),
                "countryCode2": "US",
                "radius": "30",
                "radiusUnit": "mi",
                "page": "1",
                "pageSize": str(min(query.limit, 50)),
                "fields": "id|jobId|guid|summary|title|postedDate|modifiedDate|company|location|employmentType|salary",
            }

            if query.location:
                params["location"] = query.location

            if query.remote_only:
                params["filters.isRemote"] = "true"

            headers = {
                "User-Agent": "JobSeeker-AI/1.0",
                "Accept": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL, params=params, headers=headers
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Dice API returned {response.status}")
                        return results

                    data = await response.json()
                    jobs = data.get("data", [])

                    for job in jobs:
                        try:
                            result = self._parse_job(job)
                            if result:
                                results.append(result)
                        except Exception as e:
                            logger.warning(f"Error parsing Dice job: {e}")
                            continue

        except Exception as e:
            logger.error(f"Dice search error: {e}")

        return results

    def _parse_job(self, job: dict) -> Optional[SearchResult]:
        """Parse a Dice job listing."""
        title = job.get("title", "")
        if not title:
            return None

        company = job.get("company", {})
        company_name = company.get("name") if isinstance(company, dict) else str(company)

        location = job.get("location", "")
        if isinstance(location, dict):
            location = location.get("city", "") or location.get("displayName", "")

        description = job.get("summary", "") or job.get("description", "")

        posted_date = None
        if job.get("postedDate"):
            try:
                posted_date = datetime.fromisoformat(
                    job["postedDate"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        salary_min, salary_max, salary_type = None, None, None
        salary = job.get("salary")
        if salary:
            salary_min, salary_max, salary_type = self.parse_salary(str(salary))

        job_url = f"https://www.dice.com/job-detail/{job.get('id', job.get('jobId', ''))}"

        return SearchResult(
            source="dice",
            source_id=job.get("id") or job.get("jobId"),
            title=title,
            company=company_name,
            description=description,
            url=job_url,
            location=location,
            remote="remote" in location.lower() if location else False,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_type=salary_type,
            skills=self.extract_skills(description),
            posted_date=posted_date,
            job_type=job.get("employmentType"),
            raw_data=job,
        )
