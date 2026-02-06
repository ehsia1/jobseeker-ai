"""We Work Remotely job searcher - popular remote job board using RSS feed."""

import aiohttp
import logging
import re
import xml.etree.ElementTree as ET
from typing import List, Optional
from datetime import datetime
from email.utils import parsedate_to_datetime

from backend.searchers.base import BaseJobSearcher, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class WeWorkRemotelySearcher(BaseJobSearcher):
    """Searcher for We Work Remotely - curated remote jobs via RSS."""

    # Category RSS feeds
    RSS_FEEDS = {
        "programming": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "design": "https://weworkremotely.com/categories/remote-design-jobs.rss",
        "devops": "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
        "marketing": "https://weworkremotely.com/categories/remote-marketing-jobs.rss",
        "customer-support": "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
        "sales": "https://weworkremotely.com/categories/remote-sales-jobs.rss",
        "product": "https://weworkremotely.com/categories/remote-product-jobs.rss",
        "finance": "https://weworkremotely.com/categories/remote-finance-legal-jobs.rss",
        "hr": "https://weworkremotely.com/categories/remote-hr-recruiting-jobs.rss",
        "all": "https://weworkremotely.com/remote-jobs.rss",
    }

    def __init__(self):
        super().__init__("WeWorkRemotely")

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search We Work Remotely for remote jobs via RSS feed."""
        results = []

        try:
            category = self._map_keywords_to_category(query.keywords)
            rss_url = self.RSS_FEEDS.get(category, self.RSS_FEEDS["all"])

            logger.info(f"WeWorkRemotely fetching RSS: {rss_url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(rss_url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status != 200:
                        logger.warning(f"WeWorkRemotely RSS returned {response.status}")
                        return []

                    content = await response.text()

            # Parse RSS XML
            root = ET.fromstring(content)
            channel = root.find("channel")
            if channel is None:
                return []

            items = channel.findall("item")

            for item in items[:query.limit * 2]:  # Get extra for filtering
                result = self._parse_rss_item(item, query)
                if result:
                    # Filter by keywords if specified
                    if self._matches_keywords(result, query.keywords):
                        results.append(result)
                        if len(results) >= query.limit:
                            break

            logger.info(f"Found {len(results)} jobs on WeWorkRemotely")

        except ET.ParseError as e:
            logger.error(f"WeWorkRemotely RSS parse error: {e}")
        except Exception as e:
            logger.error(f"Error searching WeWorkRemotely: {e}")

        return results

    def _parse_rss_item(self, item: ET.Element, query: SearchQuery) -> Optional[SearchResult]:
        """Parse an RSS item into a SearchResult."""
        try:
            title_elem = item.find("title")
            link_elem = item.find("link")
            desc_elem = item.find("description")
            pubdate_elem = item.find("pubDate")

            if title_elem is None or title_elem.text is None:
                return None

            title = title_elem.text.strip()
            url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
            description = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""

            # Clean HTML from description
            description = re.sub(r'<[^>]+>', '', description)

            # Parse company from title (format: "Company: Position")
            company = None
            job_title = title
            if ": " in title:
                parts = title.split(": ", 1)
                company = parts[0].strip()
                job_title = parts[1].strip() if len(parts) > 1 else title

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
                remote=True,  # All WWR jobs are remote
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
            logger.error(f"Error parsing WWR RSS item: {e}")
            return None

    def _matches_keywords(self, result: SearchResult, keywords: Optional[List[str]]) -> bool:
        """Check if result matches any of the keywords."""
        if not keywords:
            return True

        text = f"{result.title} {result.description} {result.company or ''}".lower()
        return any(kw.lower() in text for kw in keywords)

    def _map_keywords_to_category(self, keywords: Optional[List[str]]) -> str:
        """Map search keywords to WWR categories."""
        if not keywords:
            return "all"

        keyword_text = " ".join(k.lower() for k in keywords)

        category_mapping = {
            "programming": ["python", "javascript", "developer", "engineer", "software", "backend", "frontend", "fullstack", "react", "node"],
            "design": ["design", "ux", "ui", "graphic", "creative", "figma"],
            "devops": ["devops", "sysadmin", "infrastructure", "cloud", "aws", "kubernetes", "docker"],
            "marketing": ["marketing", "seo", "content", "growth", "social media"],
            "customer-support": ["support", "customer service", "help desk", "success"],
            "sales": ["sales", "business development", "account executive"],
            "product": ["product manager", "product owner", "pm"],
            "finance": ["finance", "accounting", "legal", "compliance", "cfo"],
            "hr": ["hr", "recruiting", "talent", "people ops", "recruiter"],
        }

        for category, terms in category_mapping.items():
            if any(term in keyword_text for term in terms):
                return category

        return "all"
