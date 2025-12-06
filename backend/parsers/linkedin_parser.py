"""LinkedIn email job alert parser."""

from typing import List, Dict, Any
from backend.parsers.email_parser import EmailJobParser
from backend.parsers.base import ParsedJob


class LinkedInEmailParser(EmailJobParser):
    """Parser for LinkedIn job alert emails."""
    
    def __init__(self):
        super().__init__("linkedin")
    
    def can_parse(self, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Check if this is a LinkedIn job alert email."""
        
        if not metadata:
            return False
        
        email_from = metadata.get('from', '').lower()
        subject = metadata.get('subject', '').lower()
        
        # Check for LinkedIn domain and job alert indicators
        is_linkedin = 'linkedin.com' in email_from or 'linkedin' in email_from
        is_job_alert = any(keyword in subject for keyword in [
            'job alert', 'new jobs', 'job recommendation', 'jobs you may be interested',
            'job opportunities', 'recommended for you'
        ])
        
        return is_linkedin and is_job_alert
    
    async def parse(self, content: str, metadata: Dict[str, Any] = None) -> List[ParsedJob]:
        """Parse LinkedIn email content to extract job listings."""
        
        if not self.can_parse(content, metadata):
            return []
        
        # TODO: Implement LinkedIn-specific parsing
        # For now, use the base email parser logic
        jobs = await super().parse(content, metadata)
        
        # Update source for all parsed jobs
        for job in jobs:
            job.source = self.source_name
        
        return jobs