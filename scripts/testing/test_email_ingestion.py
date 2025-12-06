#!/usr/bin/env python3
"""Test email ingestion from Gmail."""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import getpass

# Add backend to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.parsers.upwork_parser import UpworkEmailParser
from backend.parsers.linkedin_parser import LinkedInEmailParser

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


async def test_email_ingestion():
    """Test fetching and parsing emails from Gmail."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}JobSeeker AI - Email Ingestion Test{Colors.ENDC}")
    print("=" * 60)
    
    # Get email credentials
    email_address = os.getenv("EMAIL_ADDRESS", "echsia16@gmail.com")
    email_password = os.getenv("EMAIL_PASSWORD")
    
    if not email_password or email_password == "your_app_specific_password":
        print(f"\n{Colors.WARNING}Gmail App Password Required:{Colors.ENDC}")
        print("1. Go to: https://myaccount.google.com/apppasswords")
        print("2. Sign in to your Google account")
        print("3. Create an app password for 'Mail'")
        print("4. Copy the 16-character password (without spaces)")
        print()
        email_password = getpass.getpass("Enter your Gmail app password: ")
        
        # Update .env file
        update_env = input("\nSave this password to .env file? (y/n): ")
        if update_env.lower() == 'y':
            env_path = project_root / ".env"
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines):
                if line.startswith("EMAIL_PASSWORD="):
                    lines[i] = f"EMAIL_PASSWORD={email_password}\n"
                    break
            
            with open(env_path, 'w') as f:
                f.writelines(lines)
            print(f"{Colors.GREEN}✅ Password saved to .env{Colors.ENDC}")
    
    # Set credentials in environment
    os.environ["EMAIL_ADDRESS"] = email_address
    os.environ["EMAIL_PASSWORD"] = email_password
    
    print(f"\n{Colors.CYAN}Testing connection to: {email_address}{Colors.ENDC}")
    
    # Test Upwork parser
    print(f"\n{Colors.CYAN}=== Testing Upwork Email Parser ==={Colors.ENDC}")
    upwork_parser = UpworkEmailParser()
    
    try:
        print("Fetching emails from Upwork...")
        emails = await upwork_parser.fetch_emails(limit=5)
        print(f"{Colors.GREEN}✅ Found {len(emails)} Upwork emails{Colors.ENDC}")
        
        jobs_found = 0
        for i, email_data in enumerate(emails, 1):
            print(f"\n  Email {i}:")
            print(f"    From: {email_data.get('from', 'Unknown')}")
            print(f"    Subject: {email_data.get('subject', 'No subject')[:60]}...")
            print(f"    Date: {email_data.get('date', 'Unknown')}")
            
            # Parse jobs from email
            try:
                jobs = await upwork_parser.parse(
                    email_data['body'],
                    metadata={
                        'subject': email_data['subject'],
                        'from': email_data['from'],
                        'date': email_data['date']
                    }
                )
                
                if jobs:
                    print(f"    {Colors.GREEN}Jobs found: {len(jobs)}{Colors.ENDC}")
                    for job in jobs[:2]:  # Show first 2 jobs
                        print(f"      - {job.title[:50]}...")
                        if job.rate_min or job.rate_max:
                            print(f"        Rate: ${job.rate_min or 0}-${job.rate_max or 0} {job.rate_type or ''}")
                    jobs_found += len(jobs)
                else:
                    print(f"    {Colors.WARNING}No jobs parsed{Colors.ENDC}")
                    
            except Exception as e:
                print(f"    {Colors.FAIL}Parse error: {e}{Colors.ENDC}")
        
        print(f"\n{Colors.CYAN}Total Upwork jobs found: {jobs_found}{Colors.ENDC}")
        
    except Exception as e:
        print(f"{Colors.FAIL}❌ Upwork parser error: {e}{Colors.ENDC}")
        print(f"\n{Colors.WARNING}Troubleshooting:{Colors.ENDC}")
        print("1. Check your Gmail app password")
        print("2. Enable IMAP in Gmail settings")
        print("3. Check if you have Upwork emails in your inbox")
    
    # Test LinkedIn parser
    print(f"\n{Colors.CYAN}=== Testing LinkedIn Email Parser ==={Colors.ENDC}")
    linkedin_parser = LinkedInEmailParser()
    
    try:
        print("Fetching emails from LinkedIn...")
        emails = await linkedin_parser.fetch_emails(limit=5)
        print(f"{Colors.GREEN}✅ Found {len(emails)} LinkedIn emails{Colors.ENDC}")
        
        jobs_found = 0
        for i, email_data in enumerate(emails, 1):
            print(f"\n  Email {i}:")
            print(f"    From: {email_data.get('from', 'Unknown')}")
            print(f"    Subject: {email_data.get('subject', 'No subject')[:60]}...")
            
            # Parse jobs from email
            try:
                jobs = await linkedin_parser.parse(
                    email_data['body'],
                    metadata={
                        'subject': email_data['subject'],
                        'from': email_data['from'],
                        'date': email_data['date']
                    }
                )
                
                if jobs:
                    print(f"    {Colors.GREEN}Jobs found: {len(jobs)}{Colors.ENDC}")
                    for job in jobs[:2]:
                        print(f"      - {job.title[:50]}...")
                        print(f"        Company: {job.company or 'Unknown'}")
                    jobs_found += len(jobs)
                else:
                    print(f"    {Colors.WARNING}No jobs parsed{Colors.ENDC}")
                    
            except Exception as e:
                print(f"    {Colors.FAIL}Parse error: {e}{Colors.ENDC}")
        
        print(f"\n{Colors.CYAN}Total LinkedIn jobs found: {jobs_found}{Colors.ENDC}")
        
    except Exception as e:
        print(f"{Colors.FAIL}❌ LinkedIn parser error: {e}{Colors.ENDC}")
        print(f"\n{Colors.WARNING}Note: LinkedIn parser is a placeholder{Colors.ENDC}")
        print("  Implementation needed for LinkedIn email format")
    
    print(f"\n{Colors.GREEN}✅ Email ingestion test completed!{Colors.ENDC}\n")


async def main():
    """Run the test."""
    await test_email_ingestion()


if __name__ == "__main__":
    asyncio.run(main())