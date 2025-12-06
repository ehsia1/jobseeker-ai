"""RSS feed job parser for public job feeds."""

import asyncio
import feedparser
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from urllib.parse import urlparse

from backend.parsers.base import BaseJobParser, ParsedJob


class RSSJobParser(BaseJobParser):
    """Parser for RSS job feeds."""
    
    def __init__(self, source_name: str, feed_url: str):
        super().__init__(source_name)
        self.feed_url = feed_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def fetch_feed(self) -> Optional[Dict[str, Any]]:
        """Fetch RSS feed data."""
        
        try:
            response = await self.client.get(self.feed_url)
            response.raise_for_status()
            
            # Parse RSS feed
            feed = feedparser.parse(response.content)
            
            if feed.bozo and hasattr(feed, 'bozo_exception'):
                self.logger.warning(f"RSS feed parsing warning: {feed.bozo_exception}")
            
            return {
                'feed_info': feed.feed,
                'entries': feed.entries,
                'parsed_at': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching RSS feed {self.feed_url}: {e}")
            return None
    
    def can_parse(self, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Check if this parser can handle RSS content."""
        
        # Check if content looks like RSS/XML
        content_lower = content.lower().strip()
        
        rss_indicators = [
            '<?xml', '<rss', '<feed', '<channel>',
            'application/rss+xml', 'application/atom+xml'
        ]
        
        return any(indicator in content_lower for indicator in rss_indicators)
    
    async def parse(self, content: str, metadata: Dict[str, Any] = None) -> List[ParsedJob]:
        """Parse RSS content to extract job listings."""
        
        if not self.can_parse(content, metadata):
            return []
        
        # Parse RSS content directly
        feed = feedparser.parse(content)
        
        if feed.bozo and hasattr(feed, 'bozo_exception'):
            self.logger.warning(f"RSS parsing warning: {feed.bozo_exception}")
        
        jobs = []
        
        for entry in feed.entries:
            try:
                job = self._parse_rss_entry(entry)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.warning(f"Error parsing RSS entry: {e}")
                continue
        
        return jobs
    
    async def fetch_and_parse(self, limit: int = 50) -> List[ParsedJob]:
        """Fetch RSS feed and parse job listings."""
        
        feed_data = await self.fetch_feed()
        if not feed_data:
            return []
        
        jobs = []
        
        for entry in feed_data['entries'][:limit]:
            try:
                job = self._parse_rss_entry(entry)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.warning(f"Error parsing RSS entry: {e}")
                continue
        
        return jobs
    
    def _parse_rss_entry(self, entry) -> Optional[ParsedJob]:
        """Parse individual RSS entry to create ParsedJob."""
        
        # Extract title
        title = getattr(entry, 'title', '').strip()
        if not title:
            return None
        
        # Extract description/summary
        description = ""
        if hasattr(entry, 'summary'):
            description = self.clean_text(entry.summary)
        elif hasattr(entry, 'description'):
            description = self.clean_text(entry.description)
        elif hasattr(entry, 'content'):
            if isinstance(entry.content, list) and entry.content:
                description = self.clean_text(entry.content[0].get('value', ''))
        
        # Extract URL
        url = getattr(entry, 'link', '')
        
        # Extract published date
        posted_at = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                posted_at = datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass
        
        if not posted_at and hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                posted_at = datetime(*entry.updated_parsed[:6])
            except (TypeError, ValueError):
                pass
        
        # Extract location from title or description
        location = self._extract_location(title + " " + description)
        
        # Extract company (may be in author or from URL domain)
        company = None
        if hasattr(entry, 'author'):
            company = entry.author
        elif url:
            # Extract from domain
            domain = urlparse(url).netloc
            if domain:
                company = domain.replace('www.', '').split('.')[0].title()
        
        # Create parsed job
        job = ParsedJob(
            source=self.source_name,
            title=title,
            company=company,
            description=description,
            url=url,
            location=location,
            remote=self.is_remote(title + " " + description),
            skills=self.extract_skills(title + " " + description),
            posted_at=posted_at,
            raw_data={
                'rss_entry_id': getattr(entry, 'id', ''),
                'rss_tags': self._extract_tags(entry),
                'parsed_from': 'rss_feed'
            }
        )
        
        # Extract rate information
        rate_text = title + " " + description
        min_rate, max_rate, rate_type = self.extract_rate(rate_text)
        job.rate_min = min_rate
        job.rate_max = max_rate
        job.rate_type = rate_type
        
        return job
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location information from text."""
        
        import re
        
        # Common location patterns
        location_patterns = [
            r'(?:in|at|location:?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,?\s*[A-Z]{2,3})',  # City, State
            r'([A-Z][a-z]+,\s*[A-Z]{2,3})',  # City, ST
            r'([A-Z][a-z]+\s+[A-Z][a-z]+,\s*[A-Z]+)',  # City State, Country
            r'(New York|Los Angeles|San Francisco|Seattle|Austin|Boston|Chicago|Miami|Denver|Portland)',  # Major cities
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_tags(self, entry) -> List[str]:
        """Extract tags/categories from RSS entry."""
        
        tags = []
        
        if hasattr(entry, 'tags'):
            for tag in entry.tags:
                if hasattr(tag, 'term'):
                    tags.append(tag.term)
                elif isinstance(tag, str):
                    tags.append(tag)
        
        if hasattr(entry, 'category'):
            if isinstance(entry.category, str):
                tags.append(entry.category)
            elif isinstance(entry.category, list):
                tags.extend(entry.category)
        
        return tags


class RemoteOKParser(RSSJobParser):
    """Specialized parser for Remote OK RSS feed."""
    
    def __init__(self):
        super().__init__("remote_ok", "https://remoteok.io/remote-jobs.rss")
    
    def _parse_rss_entry(self, entry) -> Optional[ParsedJob]:
        """Parse Remote OK specific RSS entry."""
        
        job = super()._parse_rss_entry(entry)
        if not job:
            return None
        
        # Remote OK specific parsing
        description = job.description or ""
        
        # Extract salary from description
        import re
        
        # Remote OK format: "$50k-$100k"
        salary_pattern = r'\$(\d+)k?\s*[-–]\s*\$(\d+)k?'
        salary_match = re.search(salary_pattern, description)
        
        if salary_match:
            min_salary = int(salary_match.group(1))
            max_salary = int(salary_match.group(2))
            
            # Convert to actual values
            if min_salary < 1000:  # Assume it's in thousands
                min_salary *= 1000
                max_salary *= 1000
            
            job.rate_min = min_salary
            job.rate_max = max_salary
            job.rate_type = "annual"
        
        # Remote OK jobs are always remote
        job.remote = True
        
        # Extract company from description or title
        if not job.company:
            company_pattern = r'@\s*([A-Z][a-zA-Z\s]+?)(?:\s|$|\|)'
            company_match = re.search(company_pattern, job.title + " " + description)
            if company_match:
                job.company = company_match.group(1).strip()
        
        # Extract specific skills from Remote OK format
        tags = job.raw_data.get('rss_tags', [])
        if tags:
            # Add tags as skills
            job.skills.extend([tag.lower() for tag in tags if tag.lower() not in job.skills])
        
        return job