#!/usr/bin/env python3
"""Test script for job ingestion pipeline."""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def main():
    """Test the ingestion pipeline."""
    
    print("🔍 Testing JobSeeker AI Ingestion Pipeline...")
    
    try:
        # Import after path setup
        from backend.config import settings
        from backend.database import async_session
        from backend.services.ingestion_service import IngestionService
        
        print(f"Environment: {settings.environment}")
        print(f"Email configured: {'✅' if settings.email_address else '❌'}")
        print()
        
        # Test with database session
        async with async_session() as db:
            ingestion_service = IngestionService(db)
            
            print("📊 Testing parsers...")
            test_results = await ingestion_service.test_parsers()
            
            print("\n=== EMAIL PARSERS ===")
            for source, result in test_results.get("email_parsers", {}).items():
                status_icon = "✅" if result["status"] == "success" else "❌"
                print(f"{status_icon} {source}")
                
                if result["status"] == "success":
                    print(f"   📧 Emails fetched: {result.get('emails_fetched', 0)}")
                    print(f"   💼 Jobs parsed: {result.get('jobs_parsed', 0)}")
                    if result.get('sample_job'):
                        job = result['sample_job']
                        print(f"   📝 Sample: {job.get('title', 'N/A')[:50]}...")
                else:
                    print(f"   ❌ Error: {result.get('error', 'Unknown')}")
                print()
            
            print("=== RSS PARSERS ===")
            for source, result in test_results.get("rss_parsers", {}).items():
                status_icon = "✅" if result["status"] == "success" else "❌"
                print(f"{status_icon} {source}")
                
                if result["status"] == "success":
                    print(f"   🔗 Feed URL: {result.get('feed_url', 'N/A')}")
                    print(f"   💼 Jobs parsed: {result.get('jobs_parsed', 0)}")
                    if result.get('sample_job'):
                        job = result['sample_job']
                        print(f"   📝 Sample: {job.get('title', 'N/A')[:50]}...")
                else:
                    print(f"   ❌ Error: {result.get('error', 'Unknown')}")
                print()
            
            # Ask if user wants to run full ingestion
            print("🚀 Run full ingestion? (y/N): ", end="")
            choice = input().strip().lower()
            
            if choice == 'y':
                print("\n📥 Running full ingestion...")
                results = await ingestion_service.ingest_all_sources(limit_per_source=10)
                
                print(f"\n=== INGESTION RESULTS ===")
                print(f"📊 Total jobs processed: {results['total_jobs']}")
                print(f"📧 Email sources: {len(results['email_results'])}")
                print(f"🔗 RSS sources: {len(results['rss_results'])}")
                
                if results['errors']:
                    print(f"⚠️  Errors: {len(results['errors'])}")
                    for error in results['errors']:
                        print(f"   - {error}")
                
                print("\n✅ Ingestion complete!")
            else:
                print("\n👍 Test complete - no data ingested")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)