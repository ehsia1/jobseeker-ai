"""LangChain tools for the JobSeeker agent."""

from typing import List, Dict, Any, Optional
from langchain.tools import tool
from pydantic import BaseModel, Field
import asyncio
import logging

logger = logging.getLogger(__name__)


class JobSearchInput(BaseModel):
    """Input for job search tool."""
    keywords: List[str] = Field(description="Keywords to search for")
    profession: Optional[str] = Field(description="Professional field (e.g., software_engineer, marketing)")
    remote_only: bool = Field(default=True, description="Only search for remote jobs")
    limit: int = Field(default=10, description="Maximum number of results")


class ProfileAnalysisInput(BaseModel):
    """Input for profile analysis tool."""
    user_id: str = Field(description="User ID to analyze")


class JobScoringInput(BaseModel):
    """Input for job scoring tool."""
    job_ids: List[str] = Field(description="List of job IDs to score")
    user_id: str = Field(description="User ID for scoring context")


class ProposalGenerationInput(BaseModel):
    """Input for proposal generation tool."""
    job_id: str = Field(description="Job ID to generate proposal for")
    user_id: str = Field(description="User ID for personalization")
    tone: str = Field(default="professional", description="Tone of the proposal (professional, casual, enthusiastic)")


@tool("search_jobs", args_schema=JobSearchInput)
async def search_jobs(
    keywords: List[str],
    profession: Optional[str] = None,
    remote_only: bool = True,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search for jobs across multiple job boards.
    
    This tool searches RemoteOK, HackerNews, GitHub, and other job boards
    based on the profession and keywords provided.
    """
    try:
        from backend.services.job_search_service import JobSearchService
        from backend.database import get_async_session
        
        async with get_async_session() as db:
            service = JobSearchService(db)
            results = await service.search_by_keywords(
                keywords=keywords,
                profession=profession,
                remote_only=remote_only,
                limit_per_source=limit
            )
            
            return {
                "success": True,
                "total_results": results["total_results"],
                "source_stats": results["source_stats"],
                "jobs": results["results"][:limit]  # Return top N jobs
            }
            
    except Exception as e:
        logger.error(f"Error searching jobs: {e}")
        return {
            "success": False,
            "error": str(e),
            "jobs": []
        }


@tool("analyze_user_profile", args_schema=ProfileAnalysisInput)
async def analyze_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Analyze a user's profile to understand their skills and preferences.
    
    This tool retrieves the user's profile including skills, experience,
    preferences, and generates insights for job matching.
    """
    try:
        from backend.database import get_async_session
        from backend.models.user import UserProfile
        from sqlalchemy import select
        
        async with get_async_session() as db:
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                return {
                    "success": False,
                    "error": "Profile not found",
                    "profile": None
                }
            
            # Extract key information
            profile_summary = {
                "profession": profile.profession or "Not specified",
                "job_title": profile.job_title or "Not specified",
                "skills": profile.skills or [],
                "experience_years": profile.experience_years or 0,
                "certifications": profile.certifications or [],
                "preferences": {
                    "remote_only": profile.preferences.get("remote_only", False) if profile.preferences else False,
                    "industries": profile.preferences.get("industries", []) if profile.preferences else [],
                    "min_salary": float(profile.min_rate_usd) if profile.min_rate_usd else None
                },
                "location": profile.location or "Not specified"
            }
            
            # Generate insights
            insights = []
            if len(profile.skills) > 5:
                insights.append(f"Strong skill set with {len(profile.skills)} skills")
            if profile.experience_years and profile.experience_years > 5:
                insights.append(f"Senior level with {profile.experience_years} years of experience")
            if profile.certifications:
                insights.append(f"Has {len(profile.certifications)} professional certifications")
            if profile.preferences and profile.preferences.get("remote_only"):
                insights.append("Prefers remote work opportunities")
            
            return {
                "success": True,
                "profile": profile_summary,
                "insights": insights
            }
            
    except Exception as e:
        logger.error(f"Error analyzing profile: {e}")
        return {
            "success": False,
            "error": str(e),
            "profile": None
        }


@tool("score_jobs", args_schema=JobScoringInput)
async def score_jobs(job_ids: List[str], user_id: str) -> Dict[str, Any]:
    """
    Score a list of jobs for a specific user.
    
    This tool uses the advanced scoring algorithm to evaluate how well
    each job matches the user's profile, considering skills, experience,
    compensation, location, and other factors.
    """
    try:
        from backend.database import get_async_session
        from backend.models.user import UserProfile
        from backend.models.job import Job
        from backend.services.scoring_service import ScoringService
        from backend.services.embedding_service import EmbeddingService
        from sqlalchemy import select
        
        async with get_async_session() as db:
            # Get user profile
            profile_result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = profile_result.scalar_one_or_none()
            
            if not profile:
                return {
                    "success": False,
                    "error": "User profile not found",
                    "scored_jobs": []
                }
            
            # Initialize scoring service
            embedding_service = EmbeddingService()
            scoring_service = ScoringService(embedding_service)
            
            scored_jobs = []

            for job_id in job_ids:
                # Parse composite job_id (format: "source_sourceId" or hash)
                # e.g., "RemoteOK_1129173" -> source="RemoteOK", source_id="1129173"
                job = None
                if "_" in job_id:
                    parts = job_id.split("_", 1)
                    source = parts[0]
                    source_id = parts[1] if len(parts) > 1 else None

                    # Query by source and source_id
                    job_result = await db.execute(
                        select(Job).where(
                            Job.source == source,
                            Job.source_id == source_id
                        )
                    )
                    job = job_result.scalar_one_or_none()

                # If not found by source_id, try as UUID (backward compatibility)
                if not job:
                    try:
                        job_result = await db.execute(
                            select(Job).where(Job.id == job_id)
                        )
                        job = job_result.scalar_one_or_none()
                    except Exception:
                        pass  # Invalid UUID format, skip
                
                if job:
                    # Score the job
                    score_breakdown = scoring_service.score_job(job, profile)
                    explanation = scoring_service.generate_explanation(job, profile, score_breakdown)
                    
                    scored_jobs.append({
                        "job_id": job_id,
                        "title": job.title,
                        "company": job.company,
                        "location": job.location,
                        "remote": job.remote,
                        "total_score": score_breakdown.total_score,
                        "score_breakdown": score_breakdown.to_dict(),
                        "explanation": explanation,
                        "recommended": score_breakdown.total_score >= 40
                    })
            
            # Sort by score
            scored_jobs.sort(key=lambda x: x["total_score"], reverse=True)
            
            return {
                "success": True,
                "scored_jobs": scored_jobs,
                "top_matches": [job for job in scored_jobs if job["recommended"]]
            }
            
    except Exception as e:
        logger.error(f"Error scoring jobs: {e}")
        return {
            "success": False,
            "error": str(e),
            "scored_jobs": []
        }


@tool("generate_proposal", args_schema=ProposalGenerationInput)
async def generate_proposal(
    job_id: str,
    user_id: str,
    tone: str = "professional"
) -> Dict[str, Any]:
    """
    Generate a personalized proposal for a job application.
    
    This tool creates a tailored proposal/cover letter based on the job
    requirements and the user's profile, highlighting relevant experience
    and skills.
    """
    try:
        from backend.database import get_async_session
        from backend.models.user import UserProfile
        from backend.models.job import Job
        from sqlalchemy import select
        
        async with get_async_session() as db:
            # Parse composite job_id (format: "source_sourceId" or hash)
            job = None
            if "_" in job_id:
                parts = job_id.split("_", 1)
                source = parts[0]
                source_id = parts[1] if len(parts) > 1 else None

                job_result = await db.execute(
                    select(Job).where(
                        Job.source == source,
                        Job.source_id == source_id
                    )
                )
                job = job_result.scalar_one_or_none()

            # Fallback to UUID lookup
            if not job:
                try:
                    job_result = await db.execute(
                        select(Job).where(Job.id == job_id)
                    )
                    job = job_result.scalar_one_or_none()
                except Exception:
                    pass

            profile_result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = profile_result.scalar_one_or_none()

            if not job or not profile:
                return {
                    "success": False,
                    "error": "Job or profile not found",
                    "proposal": None
                }
            
            # Find matching skills
            job_skills = set(s.lower() for s in (job.skills or []))
            user_skills = set(s.lower() for s in (profile.skills or []))
            matching_skills = job_skills & user_skills
            
            # Create proposal template
            proposal_template = f"""
Dear Hiring Manager at {job.company},

I am writing to express my strong interest in the {job.title} position. 
With {profile.experience_years or 'several'} years of experience and expertise in 
{', '.join(list(matching_skills)[:3]) if matching_skills else 'relevant technologies'}, 
I am confident I can make valuable contributions to your team.

Key qualifications that align with your requirements:
- Proficient in {', '.join(list(matching_skills)[:5]) if matching_skills else 'the required skills'}
- {profile.experience or 'Extensive experience in the field'}
{f'- Hold certifications in {", ".join(profile.certifications[:2])}' if profile.certifications else ''}

I am particularly drawn to this opportunity because it offers the chance to work 
{f'remotely with' if job.remote else f'in {job.location} with'} a team focused on 
innovative solutions. My background aligns well with your needs, and I am excited 
about the possibility of contributing to {job.company}'s success.

I would welcome the opportunity to discuss how my skills and experience can benefit 
your team. Thank you for considering my application.

Best regards,
[Your Name]
"""
            
            # Adjust tone if needed
            if tone == "casual":
                proposal_template = proposal_template.replace("Dear Hiring Manager", "Hi there")
                proposal_template = proposal_template.replace("I am writing to express my strong interest", "I'm really excited about")
                proposal_template = proposal_template.replace("Best regards", "Cheers")
            elif tone == "enthusiastic":
                proposal_template = proposal_template.replace("strong interest", "tremendous enthusiasm")
                proposal_template = proposal_template.replace("confident", "absolutely thrilled and confident")
                proposal_template = proposal_template.replace("excited about", "incredibly excited about")
            
            return {
                "success": True,
                "proposal": proposal_template.strip(),
                "matching_skills": list(matching_skills),
                "match_percentage": len(matching_skills) / len(job_skills) * 100 if job_skills else 0
            }
            
    except Exception as e:
        logger.error(f"Error generating proposal: {e}")
        return {
            "success": False,
            "error": str(e),
            "proposal": None
        }


@tool("send_notification")
def send_notification(
    user_id: str,
    message: str,
    job_matches: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Send a notification to the user about job matches.
    
    This tool sends notifications via email, Slack, or other configured
    channels to inform users about new job opportunities.
    """
    try:
        # For now, we'll just log the notification
        # In production, this would integrate with email/Slack/etc.
        logger.info(f"Notification for user {user_id}: {message}")
        
        if job_matches:
            logger.info(f"Found {len(job_matches)} job matches")
            for match in job_matches[:3]:  # Log top 3
                logger.info(f"  - {match.get('title')} at {match.get('company')} (Score: {match.get('total_score', 0):.1f})")
        
        return {
            "success": True,
            "notification_sent": True,
            "channel": "log",  # Would be "email", "slack", etc. in production
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return {
            "success": False,
            "error": str(e),
            "notification_sent": False
        }


# Tool list for the agent
JOBSEEKER_TOOLS = [
    search_jobs,
    analyze_user_profile,
    score_jobs,
    generate_proposal,
    send_notification
]