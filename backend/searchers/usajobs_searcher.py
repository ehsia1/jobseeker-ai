"""USAJobs searcher - official US government job board."""

import aiohttp
import logging
import os
import re
from typing import List, Optional
from datetime import datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class USAJobsSearcher(BaseJobSearcher):
    """
    Searcher for USAJobs - official US federal government jobs.

    Requires API key from https://developer.usajobs.gov/
    Set USAJOBS_API_KEY and USAJOBS_EMAIL environment variables.
    """

    BASE_URL = "https://data.usajobs.gov/api/Search"

    def __init__(self):
        super().__init__("USAJobs")
        self.api_key = os.getenv("USAJOBS_API_KEY", "")
        self.user_email = os.getenv("USAJOBS_EMAIL", "")

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search USAJobs for federal government positions."""
        results = []

        # Check for API credentials
        if not self.api_key or not self.user_email:
            logger.warning("USAJobs API credentials not configured. Set USAJOBS_API_KEY and USAJOBS_EMAIL environment variables.")
            return []

        try:
            # Build query params
            params = {
                "ResultsPerPage": min(query.limit, 100),
                "Fields": "full",
            }

            # Add keyword search
            if query.keywords:
                params["Keyword"] = " ".join(query.keywords)

            # Add location
            if query.location:
                params["LocationName"] = query.location

            # Remote/telework filter
            if query.remote_only:
                params["RemoteIndicator"] = "True"

            # Salary filter
            if query.min_rate:
                # Assume annual salary for gov jobs
                params["RemunerationMinimumAmount"] = int(query.min_rate)

            if query.max_rate:
                params["RemunerationMaximumAmount"] = int(query.max_rate)

            # Required headers for authentication
            headers = {
                "Host": "data.usajobs.gov",
                "User-Agent": "JobSeeker AI Bot 1.0",
                "Authorization-Key": self.api_key,
                "Authorization-Email": self.user_email,
            }

            logger.info(f"USAJobs search: Keyword={params.get('Keyword')}, Remote={params.get('RemoteIndicator')}")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 401:
                        logger.error("USAJobs API authentication failed - check credentials")
                        return []
                    if response.status == 429:
                        logger.warning("USAJobs API rate limit reached")
                        return []
                    if response.status != 200:
                        logger.warning(f"USAJobs API returned {response.status}")
                        return []

                    data = await response.json()

            # Parse results
            search_result = data.get("SearchResult", {})
            items = search_result.get("SearchResultItems", [])

            for item in items:
                result = self._parse_job(item)
                if result:
                    results.append(result)
                    if len(results) >= query.limit:
                        break

            logger.info(f"Found {len(results)} jobs on USAJobs")

        except Exception as e:
            logger.error(f"Error searching USAJobs: {e}")

        return results

    def _parse_job(self, item: dict) -> Optional[SearchResult]:
        """Parse a USAJobs listing."""
        try:
            matched = item.get("MatchedObjectDescriptor", {})

            title = matched.get("PositionTitle", "")
            if not title:
                return None

            # Get organization/agency
            company = matched.get("OrganizationName", "")
            department = matched.get("DepartmentName", "")
            if department and company:
                company = f"{company} ({department})"

            # Get description from UserArea
            user_area = matched.get("UserArea", {})
            details = user_area.get("Details", {})

            # Build description from multiple fields
            description_parts = []
            if details.get("JobSummary"):
                description_parts.append(details.get("JobSummary"))
            if details.get("MajorDuties"):
                duties = details.get("MajorDuties", [])
                if isinstance(duties, list):
                    description_parts.append("Duties: " + "; ".join(duties[:5]))
                elif isinstance(duties, str):
                    description_parts.append("Duties: " + duties)
            if details.get("Requirements"):
                description_parts.append("Requirements: " + str(details.get("Requirements"))[:500])

            description = " ".join(description_parts)
            if not description:
                description = matched.get("QualificationSummary", "") or title

            # Clean HTML
            description = re.sub(r'<[^>]+>', ' ', description)
            description = re.sub(r'\s+', ' ', description).strip()

            # Get location
            locations = matched.get("PositionLocation", [])
            location_str = "United States"
            if locations and isinstance(locations, list):
                loc = locations[0]
                city = loc.get("CityName", "")
                state = loc.get("CountrySubDivisionCode", "")
                if city and state:
                    location_str = f"{city}, {state}"
                elif loc.get("LocationName"):
                    location_str = loc.get("LocationName")

            # Check remote
            remote = False
            if details.get("TeleworkEligible") == "True":
                remote = True
            if "remote" in (description + title).lower():
                remote = True

            # Get salary
            remuneration = matched.get("PositionRemuneration", [])
            salary_min, salary_max, salary_type = None, None, None
            if remuneration and isinstance(remuneration, list):
                rem = remuneration[0]
                salary_min = rem.get("MinimumRange")
                salary_max = rem.get("MaximumRange")
                rate_type = rem.get("RateIntervalCode", "")
                if rate_type == "PA" or rate_type == "Per Year":
                    salary_type = "annual"
                elif rate_type == "PH" or rate_type == "Per Hour":
                    salary_type = "hourly"
                else:
                    salary_type = "annual"  # Default for gov jobs

                # Convert to float
                try:
                    salary_min = float(salary_min) if salary_min else None
                    salary_max = float(salary_max) if salary_max else None
                except (ValueError, TypeError):
                    pass

            # Get URLs
            url = matched.get("PositionURI", "")
            apply_url = matched.get("ApplyURI", [""])[0] if matched.get("ApplyURI") else url

            # Parse date
            posted_date = None
            pub_date = matched.get("PublicationStartDate")
            if pub_date:
                try:
                    posted_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                except Exception:
                    pass

            # Get job type
            schedule = matched.get("PositionSchedule", [])
            job_type = None
            if schedule and isinstance(schedule, list):
                sched = schedule[0].get("Name", "")
                if "full" in sched.lower():
                    job_type = "full-time"
                elif "part" in sched.lower():
                    job_type = "part-time"

            # Extract skills
            skills = self.extract_skills(description)

            # Add qualifications as skills
            quals = details.get("QualificationsRequired")
            if quals:
                quals_skills = self.extract_skills(str(quals))
                skills.extend(quals_skills)
                skills = list(set(skills))[:20]

            return SearchResult(
                source=self.source_name,
                source_id=item.get("MatchedObjectId"),
                title=title,
                company=company,
                description=description[:2000],
                url=url or apply_url,
                location=location_str,
                remote=remote,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_type=salary_type,
                skills=skills,
                posted_date=posted_date,
                job_type=job_type,
                experience_level=None,
                raw_data=item
            )

        except Exception as e:
            logger.error(f"Error parsing USAJobs listing: {e}")
            return None
