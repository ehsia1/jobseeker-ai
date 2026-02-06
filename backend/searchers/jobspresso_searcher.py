"""Jobspresso job searcher - curated remote jobs via RSS."""

import aiohttp
import logging
import re
import xml.etree.ElementTree as ET
from typing import List, Optional
from datetime import datetime
from email.utils import parsedate_to_datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class JobspressoSearcher(BaseJobSearcher):
    """Searcher for Jobspresso - expertly curated remote jobs via RSS feed."""

    RSS_URL = "https://jobspresso.co/jobs/feed/"

    def __init__(self):
        super().__init__("Jobspresso")

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Jobspresso for curated remote jobs via RSS."""
        results = []

        try:
            logger.info(f"Jobspresso fetching RSS: {self.RSS_URL}")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.RSS_URL,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Jobspresso RSS returned {response.status}")
                        return []

                    content = await response.text()

            # Parse RSS XML
            root = ET.fromstring(content)
            channel = root.find("channel")
            if channel is None:
                return []

            items = channel.findall("item")

            for item in items[:query.limit * 2]:  # Get extra for filtering
                result = self._parse_rss_item(item)
                if result:
                    # Filter by keywords if specified
                    if self._matches_keywords(result, query.keywords):
                        results.append(result)
                        if len(results) >= query.limit:
                            break

            logger.info(f"Found {len(results)} jobs on Jobspresso")

        except ET.ParseError as e:
            logger.error(f"Jobspresso RSS parse error: {e}")
        except Exception as e:
            logger.error(f"Error searching Jobspresso: {e}")

        return results

    def _parse_rss_item(self, item: ET.Element) -> Optional[SearchResult]:
        """Parse an RSS item into a SearchResult."""
        try:
            title_elem = item.find("title")
            link_elem = item.find("link")
            desc_elem = item.find("description")
            pubdate_elem = item.find("pubDate")

            # Company is in dc:creator field with namespace
            dc_ns = {"dc": "http://purl.org/dc/elements/1.1/"}
            creator_elem = item.find("dc:creator", dc_ns)

            if title_elem is None or title_elem.text is None:
                return None

            title = title_elem.text.strip()
            url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
            description = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""

            # Clean HTML from description
            description = re.sub(r'<[^>]+>', '', description)

            # Parse company from dc:creator (format: "Company<br>⚲&nbsp;Location")
            company = None
            job_title = title
            if creator_elem is not None and creator_elem.text:
                creator_text = creator_elem.text.strip()
                # Clean HTML and extract company name (before <br> tag)
                company = re.sub(r'<.*', '', creator_text).strip()
            elif " at " in title:
                # Fallback: parse from title
                parts = title.rsplit(" at ", 1)
                job_title = parts[0].strip()
                company = parts[1].strip() if len(parts) > 1 else None

            # Parse date
            posted_date = None
            if pubdate_elem is not None and pubdate_elem.text:
                try:
                    posted_date = parsedate_to_datetime(pubdate_elem.text)
                except Exception:
                    pass

            # Extract skills from description
            skills = self.extract_skills(description)

            # Parse salary if mentioned
            salary_min, salary_max, salary_type = self.parse_salary(description)

            return SearchResult(
                source=self.source_name,
                source_id=url,  # Use URL as unique ID
                title=job_title,
                company=company,
                description=description[:2000],
                url=url,
                location="Remote",
                remote=True,  # All Jobspresso jobs are remote
                salary_min=salary_min,
                salary_max=salary_max,
                salary_type=salary_type,
                skills=skills[:20],
                posted_date=posted_date,
                job_type=None,
                experience_level=None,
                raw_data={"title": title, "description": description}
            )

        except Exception as e:
            logger.error(f"Error parsing Jobspresso RSS item: {e}")
            return None

    def _matches_keywords(self, result: SearchResult, keywords: Optional[List[str]]) -> bool:
        """Check if result matches any of the keywords."""
        if not keywords:
            return True

        text = f"{result.title} {result.description} {result.company or ''}".lower()
        return any(kw.lower() in text for kw in keywords)
