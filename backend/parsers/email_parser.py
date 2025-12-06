"""Email-based job parser for job alerts."""

import asyncio
import imaplib
import email
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional
from datetime import datetime
import ssl
from bs4 import BeautifulSoup

from backend.parsers.base import BaseJobParser, ParsedJob
from backend.config import settings


class EmailJobParser(BaseJobParser):
    """Base class for parsing job alerts from email."""
    
    def __init__(self, source_name: str):
        super().__init__(source_name)
        self.imap_server = settings.email_imap_server
        self.imap_port = settings.email_imap_port
        self.email_address = settings.email_address
        self.email_password = settings.email_password
    
    async def fetch_emails(self, folder: str = "INBOX", limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch recent emails from IMAP server.
        
        Args:
            folder: Email folder to search
            limit: Maximum number of emails to fetch
            
        Returns:
            List of email data dictionaries
        """
        
        if not self.email_address or not self.email_password:
            self.logger.warning("Email credentials not configured")
            return []
        
        try:
            # Connect to IMAP server
            context = ssl.create_default_context()
            
            with imaplib.IMAP4_SSL(self.imap_server, self.imap_port, ssl_context=context) as imap:
                imap.login(self.email_address, self.email_password)
                imap.select(folder)
                
                # Search for recent emails from job platforms
                search_criteria = self._get_search_criteria()
                typ, message_numbers = imap.search(None, search_criteria)
                
                if typ != 'OK':
                    self.logger.error("Failed to search emails")
                    return []
                
                emails = []
                message_ids = message_numbers[0].split()
                
                # Get recent emails (limit)
                for msg_id in message_ids[-limit:]:
                    typ, msg_data = imap.fetch(msg_id, '(RFC822)')
                    if typ == 'OK':
                        email_body = msg_data[0][1]
                        email_message = email.message_from_bytes(email_body)
                        
                        emails.append({
                            'id': msg_id.decode(),
                            'message': email_message,
                            'subject': email_message.get('Subject', ''),
                            'from': email_message.get('From', ''),
                            'date': email_message.get('Date', ''),
                            'body': self._extract_email_body(email_message)
                        })
                
                self.logger.info(f"Fetched {len(emails)} emails from {folder}")
                return emails
                
        except Exception as e:
            self.logger.error(f"Error fetching emails: {e}")
            return []
    
    def _get_search_criteria(self) -> str:
        """Get IMAP search criteria for job-related emails."""
        
        # Search for emails from job platforms in the last 7 days
        criteria_parts = [
            'UNSEEN',  # Unread emails
            '(OR (FROM "upwork.com")',
            '(OR (FROM "linkedin.com")',
            '(OR (FROM "indeed.com")',
            '(OR (FROM "remoteok.io")',
            '(FROM "weworkremotely.com")))))'
        ]
        
        return ' '.join(criteria_parts)
    
    def _extract_email_body(self, email_message) -> str:
        """Extract text content from email message."""
        
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    charset = part.get_content_charset() or 'utf-8'
                    body = part.get_payload(decode=True).decode(charset, errors='ignore')
                    break
                elif content_type == "text/html":
                    charset = part.get_content_charset() or 'utf-8'
                    html_body = part.get_payload(decode=True).decode(charset, errors='ignore')
                    # Convert HTML to text
                    soup = BeautifulSoup(html_body, 'html.parser')
                    body = soup.get_text()
        else:
            content_type = email_message.get_content_type()
            charset = email_message.get_content_charset() or 'utf-8'
            
            if content_type == "text/plain":
                body = email_message.get_payload(decode=True).decode(charset, errors='ignore')
            elif content_type == "text/html":
                html_body = email_message.get_payload(decode=True).decode(charset, errors='ignore')
                soup = BeautifulSoup(html_body, 'html.parser')
                body = soup.get_text()
        
        return self.clean_text(body)
    
    def can_parse(self, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Check if this parser can handle the email content."""
        
        if not metadata:
            return False
        
        email_from = metadata.get('from', '').lower()
        subject = metadata.get('subject', '').lower()
        
        # Check if email is from a supported platform
        supported_domains = [
            'upwork.com', 'linkedin.com', 'indeed.com',
            'remoteok.io', 'weworkremotely.com'
        ]
        
        domain_match = any(domain in email_from for domain in supported_domains)
        
        # Check if subject contains job-related keywords
        job_keywords = [
            'job alert', 'new job', 'job notification', 'job match',
            'opportunities', 'position', 'role', 'opening'
        ]
        
        subject_match = any(keyword in subject for keyword in job_keywords)
        
        return domain_match and subject_match
    
    async def parse(self, content: str, metadata: Dict[str, Any] = None) -> List[ParsedJob]:
        """Parse email content to extract job listings."""
        
        # This is a base implementation - subclasses should override
        # for platform-specific parsing logic
        
        if not self.can_parse(content, metadata):
            return []
        
        # Extract basic job information
        jobs = []
        
        # Look for job URLs in the content
        import re
        url_pattern = r'https?://[^\s<>"{}|\\^`[\]]+'
        urls = re.findall(url_pattern, content)
        
        # Filter for job-related URLs
        job_urls = [url for url in urls if self._is_job_url(url)]
        
        for url in job_urls:
            job = ParsedJob(
                source=self.source_name,
                title="Job from email alert",  # Will be extracted by specific parser
                url=url,
                description=content[:500],  # First 500 chars as description
                skills=self.extract_skills(content),
                remote=self.is_remote(content),
                posted_at=self._parse_email_date(metadata.get('date')) if metadata else None,
                raw_data={
                    'email_subject': metadata.get('subject') if metadata else None,
                    'email_from': metadata.get('from') if metadata else None,
                    'content_preview': content[:200]
                }
            )
            
            # Extract rate information
            min_rate, max_rate, rate_type = self.extract_rate(content)
            job.rate_min = min_rate
            job.rate_max = max_rate
            job.rate_type = rate_type
            
            jobs.append(job)
        
        return jobs
    
    def _is_job_url(self, url: str) -> bool:
        """Check if URL is likely a job posting."""
        
        job_url_patterns = [
            'upwork.com/jobs/',
            'linkedin.com/jobs/',
            'indeed.com/viewjob',
            'remoteok.io/remote-jobs/',
            'weworkremotely.com/remote-jobs/'
        ]
        
        return any(pattern in url.lower() for pattern in job_url_patterns)
    
    def _parse_email_date(self, date_str: str) -> Optional[datetime]:
        """Parse email date string to datetime."""
        
        if not date_str:
            return None
        
        try:
            import email.utils
            timestamp = email.utils.parsedate_tz(date_str)
            if timestamp:
                return datetime.fromtimestamp(email.utils.mktime_tz(timestamp))
        except Exception as e:
            self.logger.warning(f"Failed to parse email date '{date_str}': {e}")
        
        return None