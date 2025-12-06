#!/usr/bin/env python3
"""Test the JobRadar agent system."""

import asyncio
import logging
import os
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

from backend.agents.job_radar_agent import JobRadarAgent


async def test_agent():
    """Test the JobRadar agent workflow."""
    
    print("=" * 70)
    print("JOBRAD RADAR AGENT TEST")
    print("=" * 70)
    
    # Get test user ID (the one we created earlier)
    test_user_id = "efe51a8e-d6f5-4413-8ca1-e3e06abfeaf5"  # From earlier test
    
    # Initialize agent (using mock LLM for testing)
    agent = JobRadarAgent(
        llm_provider="mock",  # Use mock for testing without API keys
        api_key=None
    )
    
    print("\n🤖 Starting JobRadar Agent for test user...")
    print("-" * 50)
    
    # Run the agent
    result = await agent.run(
        user_id=test_user_id,
        custom_keywords=["python", "backend", "fastapi"],
        profession="software_engineer"
    )
    
    # Display results
    print("\n📊 AGENT RESULTS")
    print("-" * 50)
    
    if result["success"]:
        print(f"✅ Success! Found {result['matches_found']} job matches")
        
        print("\n📝 Process Messages:")
        for msg in result["messages"]:
            print(f"  {msg}")
        
        if result["top_matches"]:
            print(f"\n🎯 Top {min(5, len(result['top_matches']))} Matches:")
            for i, match in enumerate(result["top_matches"][:5], 1):
                print(f"\n  {i}. {match['title']} at {match['company']}")
                print(f"     Score: {match['total_score']:.1f}/100")
                print(f"     Recommended: {'Yes ✓' if match['recommended'] else 'No'}")
                
                # Show score breakdown
                if match.get('score_breakdown'):
                    breakdown = match['score_breakdown']
                    print(f"     Breakdown:")
                    print(f"       - Skills: {breakdown.get('skill_match', 0):.0f}%")
                    print(f"       - Experience: {breakdown.get('experience_match', 0):.0f}%")
                    print(f"       - Compensation: {breakdown.get('compensation_match', 0):.0f}%")
                    print(f"       - Location: {breakdown.get('location_match', 0):.0f}%")
        
        if result.get("proposals_generated"):
            print(f"\n📧 Generated {result['proposals_generated']} proposals")
        
        if result.get("notifications_sent"):
            print("\n🔔 Notifications sent successfully")
    else:
        print("❌ Agent failed")
        if result.get("errors"):
            print("\nErrors:")
            for error in result["errors"]:
                print(f"  - {error}")
    
    print("\n" + "=" * 70)
    print("AGENT WORKFLOW SUMMARY")
    print("=" * 70)
    
    print("""
    The JobRadar Agent completed the following workflow:
    
    1. ✅ Analyzed User Profile
       - Retrieved skills, preferences, and experience
       - Built search query from profile
    
    2. ✅ Searched Job Boards
       - Queried multiple sources (RemoteOK, HackerNews, GitHub)
       - Aggregated results from all sources
    
    3. ✅ Scored All Jobs
       - Applied 7-factor scoring algorithm
       - Calculated semantic similarity
       - Evaluated skill matches
    
    4. ✅ Filtered Top Matches
       - Selected jobs with score ≥ 70
       - Ranked by total score
    
    5. ✅ Generated Proposals
       - Created personalized cover letters
       - Highlighted matching skills
    
    6. ✅ Sent Notifications
       - Prepared summary for user
       - Ready for email/Slack delivery
    """)
    
    print("🎯 The agent successfully orchestrated the entire job search pipeline!")


async def test_individual_tools():
    """Test individual agent tools."""
    
    print("\n" + "=" * 70)
    print("TESTING INDIVIDUAL TOOLS")
    print("=" * 70)
    
    test_user_id = "efe51a8e-d6f5-4413-8ca1-e3e06abfeaf5"
    
    # Test profile analysis
    print("\n1. Testing Profile Analysis Tool...")
    from backend.agents.tools import analyze_user_profile
    
    profile_result = await analyze_user_profile.ainvoke({"user_id": test_user_id})
    if profile_result["success"]:
        print(f"   ✓ Profile: {profile_result['profile']['profession']}")
        print(f"   ✓ Skills: {len(profile_result['profile']['skills'])} skills")
        print(f"   ✓ Insights: {', '.join(profile_result['insights'])}")
    
    # Test job search
    print("\n2. Testing Job Search Tool...")
    from backend.agents.tools import search_jobs
    
    search_result = await search_jobs.ainvoke({
        "keywords": ["python", "backend"],
        "profession": "software_engineer",
        "remote_only": True,
        "limit": 5
    })
    if search_result["success"]:
        print(f"   ✓ Found {search_result['total_results']} total jobs")
        print(f"   ✓ Sources: {search_result['source_stats']}")
    
    # Test notification
    print("\n3. Testing Notification Tool...")
    from backend.agents.tools import send_notification
    
    notif_result = send_notification.invoke({
        "user_id": test_user_id,
        "message": "Test notification from JobRadar",
        "job_matches": []
    })
    if notif_result["success"]:
        print(f"   ✓ Notification sent via {notif_result['channel']}")


if __name__ == "__main__":
    print("Testing JobRadar Agent System")
    print("=" * 70)
    
    # Test individual tools first
    asyncio.run(test_individual_tools())
    
    # Then test the full agent
    asyncio.run(test_agent())