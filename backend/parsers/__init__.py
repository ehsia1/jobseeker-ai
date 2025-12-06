"""Job parsers for different platforms."""

from backend.parsers.base import BaseJobParser
from backend.parsers.email_parser import EmailJobParser
from backend.parsers.upwork_parser import UpworkEmailParser
from backend.parsers.linkedin_parser import LinkedInEmailParser
from backend.parsers.rss_parser import RSSJobParser

# RemoteOKParser will be implemented as an RSS parser
class RemoteOKParser(RSSJobParser):
    """Parser for Remote OK RSS feed."""
    
    def __init__(self):
        super().__init__(
            feed_url="https://remoteok.io/rss",
            source_name="RemoteOK"
        )

__all__ = [
    "BaseJobParser",
    "EmailJobParser",
    "UpworkEmailParser",
    "LinkedInEmailParser", 
    "RSSJobParser",
    "RemoteOKParser",
]