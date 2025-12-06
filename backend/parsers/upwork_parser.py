"""Upwork email job alert parser."""

import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from datetime import datetime

from backend.parsers.email_parser import EmailJobParser
from backend.parsers.base import ParsedJob


class UpworkEmailParser(EmailJobParser):
    """Parser for Upwork job alert emails."""
    
    def __init__(self):
        super().__init__("upwork")
    
    def can_parse(self, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Check if this is an Upwork job alert email."""
        
        if not metadata:
            return False
        
        email_from = metadata.get('from', '').lower()
        subject = metadata.get('subject', '').lower()
        
        # Check for Upwork domain and job alert indicators
        is_upwork = 'upwork.com' in email_from or 'upwork' in email_from
        is_job_alert = any(keyword in subject for keyword in [
            'job alert', 'new jobs', 'job matches', 'recommended jobs',
            'jobs matching', 'job notification'
        ])
        
        return is_upwork and is_job_alert
    
    async def parse(self, content: str, metadata: Dict[str, Any] = None) -> List[ParsedJob]:
        """Parse Upwork email content to extract job listings."""
        
        if not self.can_parse(content, metadata):
            return []
        
        jobs = []
        
        # Parse HTML content if available
        soup = BeautifulSoup(content, 'html.parser')
        
        # Upwork emails typically have job blocks with specific patterns
        job_blocks = self._find_job_blocks(soup, content)
        
        for block_data in job_blocks:
            try:
                job = self._parse_job_block(block_data, metadata)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.warning(f"Error parsing Upwork job block: {e}")
                continue
        
        # If no structured blocks found, try fallback parsing
        if not jobs:
            jobs = await self._fallback_parse(content, metadata)
        
        return jobs
    
    def _find_job_blocks(self, soup: BeautifulSoup, content: str) -> List[Dict[str, Any]]:
        """Find job listing blocks in Upwork email."""
        
        job_blocks = []
        
        # Look for job title links (common pattern in Upwork emails)
        job_links = soup.find_all('a', href=re.compile(r'upwork\.com/jobs/'))
        
        for link in job_links:
            block = {
                'title_element': link,
                'title': link.get_text(strip=True),
                'url': link.get('href'),
                'content_block': link.find_parent(['div', 'td', 'section'])
            }
            
            # Find surrounding content
            parent = link.find_parent(['div', 'td', 'section', 'table'])
            if parent:
                block['full_content'] = parent.get_text(strip=True)
            else:
                block['full_content'] = link.get_text(strip=True)
            
            job_blocks.append(block)
        
        # Alternative: Look for job titles without links
        if not job_blocks:
            # Pattern for job titles in plain text
            title_pattern = r'^([A-Z][^.!?]*(?:Developer|Engineer|Manager|Designer|Writer|Analyst|Specialist)[^.!?]*)'
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                line = line.strip()
                if re.match(title_pattern, line) and len(line) > 10:
                    # Get surrounding context
                    context_start = max(0, i - 2)
                    context_end = min(len(lines), i + 8)
                    context = '\n'.join(lines[context_start:context_end])
                    
                    job_blocks.append({
                        'title': line,
                        'full_content': context,
                        'url': self._extract_url_from_context(context)
                    })
        
        return job_blocks
    
    def _parse_job_block(self, block_data: Dict[str, Any], email_metadata: Dict[str, Any]) -> ParsedJob:
        """Parse individual job block to create ParsedJob."""
        
        title = block_data.get('title', '').strip()
        url = block_data.get('url', '')
        content = block_data.get('full_content', '')
        
        if not title:
            return None
        
        # Extract job ID from URL
        source_id = None
        if url:
            job_id_match = re.search(r'/jobs/[^/]*~([a-f0-9]+)', url)
            if job_id_match:
                source_id = job_id_match.group(1)
        
        # Extract company name (often in format "Company Name seeks...")
        company = self._extract_company(title, content)
        
        # Extract description from content
        description = self._extract_description(content)
        
        # Parse rate information
        min_rate, max_rate, rate_type = self.extract_rate(content)
        
        # Extract skills
        skills = self.extract_skills(content)
        
        # Extract requirements
        requirements = self._extract_requirements(content)
        
        # Check if remote
        remote = self.is_remote(content)
        
        # Extract duration and hours
        duration = self._extract_duration(content)
        hours_per_week = self._extract_hours_per_week(content)
        
        job = ParsedJob(
            source=self.source_name,
            source_id=source_id,
            title=title,
            company=company,
            description=description,
            url=url,
            requirements=requirements,
            skills=skills,
            rate_min=min_rate,
            rate_max=max_rate,
            rate_type=rate_type,
            remote=remote,
            duration=duration,
            hours_per_week=hours_per_week,
            posted_at=datetime.now(),  # Email arrival time as proxy
            raw_data={
                'email_subject': email_metadata.get('subject'),
                'email_from': email_metadata.get('from'),
                'content_block': content[:500],
                'parsed_from': 'upwork_email'
            }
        )
        
        return job
    
    def _extract_company(self, title: str, content: str) -> str:
        """Extract company name from job title or content."""
        
        # Pattern: "Company Name seeks Developer"
        seeks_pattern = r'^([^-]+?)\s+seeks?\s+'
        match = re.search(seeks_pattern, title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Pattern: "Developer needed by Company Name"
        by_pattern = r'\s+by\s+([^.!?\n]+)'
        match = re.search(by_pattern, title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Look in content for "Client:" or "Company:"
        client_pattern = r'(?:Client|Company):\s*([^\n.!?]+)'
        match = re.search(client_pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _extract_description(self, content: str) -> str:
        """Extract job description from content block."""
        
        lines = content.split('\n')
        description_lines = []
        
        # Skip first few lines (usually title/metadata)
        start_found = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Start collecting after we see description indicators
            if not start_found:
                if any(indicator in line.lower() for indicator in [
                    'description', 'about', 'we are looking', 'seeking', 'need'
                ]):
                    start_found = True
                continue
            
            # Stop at certain patterns
            if any(stopper in line.lower() for stopper in [
                'skills required', 'budget', 'hourly range', 'fixed price',
                'apply now', 'click here'
            ]):
                break
            
            description_lines.append(line)
        
        description = ' '.join(description_lines)
        return self.clean_text(description)[:1000]  # Limit length
    
    def _extract_requirements(self, content: str) -> List[str]:
        """Extract job requirements from content."""
        
        requirements = []
        
        # Look for requirements section
        req_patterns = [
            r'(?:Skills?|Requirements?|Qualifications?)[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)',
            r'(?:Must have|Required)[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)',
            r'(?:Experience with|Proficient in)[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)'
        ]
        
        for pattern in req_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Split on common separators
                items = re.split(r'[,\n\-•]', match)
                for item in items:
                    item = item.strip()
                    if item and len(item) > 3:
                        requirements.append(item)
        
        return requirements[:10]  # Limit to 10 requirements
    
    def _extract_duration(self, content: str) -> str:
        """Extract project duration from content."""
        
        duration_patterns = [
            r'Duration[:\s]*([^.\n]+)',
            r'Project length[:\s]*([^.\n]+)',
            r'Timeline[:\s]*([^.\n]+)',
            r'(\d+\s*(?:weeks?|months?|days?))',
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_hours_per_week(self, content: str) -> int:
        """Extract hours per week from content."""
        
        hours_patterns = [
            r'(\d+)\s*(?:hours?|hrs?)\s*per\s*week',
            r'(\d+)\s*(?:hours?|hrs?)/week',
            r'Hours per week[:\s]*(\d+)',
        ]
        
        for pattern in hours_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        # Look for common time commitments
        if 'full time' in content.lower() or 'full-time' in content.lower():
            return 40
        elif 'part time' in content.lower() or 'part-time' in content.lower():
            return 20
        
        return None
    
    def _extract_url_from_context(self, context: str) -> str:
        """Extract Upwork job URL from context."""
        
        url_pattern = r'https://(?:www\.)?upwork\.com/jobs/[^\s<>"{}|\\^`[\]]+'
        match = re.search(url_pattern, context)
        return match.group(0) if match else None
    
    async def _fallback_parse(self, content: str, metadata: Dict[str, Any]) -> List[ParsedJob]:
        """Fallback parsing when structured parsing fails."""
        
        # Simple fallback - look for any job URLs and create basic entries
        jobs = []
        urls = re.findall(r'https://(?:www\.)?upwork\.com/jobs/[^\s<>"{}|\\^`[\]]+', content)
        
        for url in urls:
            job = ParsedJob(
                source=self.source_name,
                title="Upwork Job (from email alert)",
                url=url,
                description=content[:300],
                skills=self.extract_skills(content),
                remote=self.is_remote(content),
                posted_at=datetime.now(),
                raw_data={
                    'email_subject': metadata.get('subject'),
                    'parsing_method': 'fallback',
                    'content_preview': content[:200]
                }
            )
            
            # Extract rate
            min_rate, max_rate, rate_type = self.extract_rate(content)
            job.rate_min = min_rate
            job.rate_max = max_rate
            job.rate_type = rate_type
            
            jobs.append(job)
        
        return jobs