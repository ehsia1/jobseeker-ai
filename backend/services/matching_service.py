"""Job matching service for generating personalized recommendations."""

import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, not_
from datetime import datetime, timedelta
import numpy as np
import logging

from backend.models.user import User, UserProfile
from backend.models.job import Job, JobMatch
from backend.models.feedback import UserFeedback
from backend.services.scoring_service import ScoringService, ScoreBreakdown
from backend.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class MatchingService:
    """Service for matching jobs to user profiles."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.scoring_service = ScoringService(self.embedding_service)
    
    async def generate_matches_for_user(
        self,
        user_id: str,
        limit: int = 20,
        min_score: float = 70.0,
        days_back: int = 7
    ) -> List[JobMatch]:
        """
        Generate job matches for a specific user.
        
        Args:
            user_id: User ID to generate matches for
            limit: Maximum number of matches to generate
            min_score: Minimum score threshold
            days_back: How many days back to look for jobs
            
        Returns:
            List of JobMatch objects
        """
        
        logger.info(f"Generating matches for user {user_id}")
        
        # Get user profile
        profile_result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = profile_result.scalar_one_or_none()
        
        if not profile:
            logger.warning(f"No profile found for user {user_id}")
            return []
        
        # Get recent jobs that haven't been matched yet
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get already matched job IDs
        existing_matches_result = await self.db.execute(
            select(JobMatch.job_id).where(JobMatch.user_id == user_id)
        )
        existing_job_ids = [row[0] for row in existing_matches_result.all()]
        
        # Query for new jobs
        jobs_query = select(Job).where(
            and_(
                Job.created_at >= cutoff_date,
                not_(Job.id.in_(existing_job_ids)) if existing_job_ids else True
            )
        ).order_by(desc(Job.posted_at))
        
        jobs_result = await self.db.execute(jobs_query)
        jobs = jobs_result.scalars().all()
        
        logger.info(f"Found {len(jobs)} potential jobs to match")
        
        # Get user feedback history for context
        context = await self._get_user_context(user_id)
        
        # Generate profile embedding if not exists
        if not profile.profile_embedding:
            profile_embedding = self.embedding_service.generate_profile_embedding(profile)
            profile.profile_embedding = profile_embedding.tolist()
            await self.db.commit()
        
        # Score and match jobs
        matches = []
        
        for job in jobs:
            try:
                # Generate job embedding if not exists
                if not job.embedding:
                    job_dict = self._job_to_dict(job)
                    job_embedding = self.embedding_service.generate_job_embedding(job_dict)
                    job.embedding = job_embedding.tolist()
                
                # Score the job using new scoring service
                score_breakdown = self.scoring_service.score_job(job, profile)
                
                # Create match if score meets threshold
                if score_breakdown.total_score >= min_score:
                    # Generate explanation
                    explanation = self.scoring_service.generate_explanation(job, profile, score_breakdown)
                    
                    match = JobMatch(
                        user_id=user_id,
                        job_id=job.id,
                        score=score_breakdown.total_score,
                        score_breakdown=score_breakdown.to_dict(),
                        explanation=explanation,
                        status="new"
                    )
                    
                    self.db.add(match)
                    matches.append(match)
                    
                    logger.debug(f"Created match: {job.title} (score: {score_breakdown.total_score:.1f})")
                
            except Exception as e:
                logger.error(f"Error scoring job {job.id}: {e}")
                continue
        
        # Commit all matches
        if matches:
            await self.db.commit()
            logger.info(f"Created {len(matches)} new matches for user {user_id}")
        
        # Sort by score and limit
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:limit]
    
    async def generate_matches_for_all_active_users(self, limit_per_user: int = 20) -> Dict[str, Any]:
        """
        Generate matches for all active users.
        
        Args:
            limit_per_user: Maximum matches per user
            
        Returns:
            Summary of matching results
        """
        
        logger.info("Starting batch matching for all active users")
        
        # Get active users with profiles
        users_result = await self.db.execute(
            select(User).where(User.is_active == True)
        )
        users = users_result.scalars().all()
        
        results = {
            "total_users": len(users),
            "successful_users": 0,
            "total_matches": 0,
            "errors": []
        }
        
        for user in users:
            try:
                matches = await self.generate_matches_for_user(
                    user.id,
                    limit=limit_per_user
                )
                
                if matches:
                    results["successful_users"] += 1
                    results["total_matches"] += len(matches)
                
            except Exception as e:
                error_msg = f"Error matching for user {user.id}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        logger.info(f"Batch matching complete: {results['total_matches']} matches for {results['successful_users']} users")
        
        return results
    
    async def recalculate_match_score(self, match_id: str) -> Optional[JobMatch]:
        """
        Recalculate score for an existing match.
        
        Args:
            match_id: Match ID to recalculate
            
        Returns:
            Updated JobMatch or None
        """
        
        # Get match with job and user profile
        match_result = await self.db.execute(
            select(JobMatch).where(JobMatch.id == match_id)
        )
        match = match_result.scalar_one_or_none()
        
        if not match:
            return None
        
        # Get job and profile
        job_result = await self.db.execute(
            select(Job).where(Job.id == match.job_id)
        )
        job = job_result.scalar_one()
        
        profile_result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == match.user_id)
        )
        profile = profile_result.scalar_one()
        
        # Get updated context
        context = await self._get_user_context(match.user_id)
        
        # Recalculate score using new scoring service
        score_breakdown = self.scoring_service.score_job(job, profile)
        
        # Generate new explanation
        explanation = self.scoring_service.generate_explanation(job, profile, score_breakdown)
        
        # Update match
        match.score = score_breakdown.total_score
        match.score_breakdown = score_breakdown.to_dict()
        match.explanation = explanation
        
        await self.db.commit()
        
        return match
    
    async def get_similar_jobs(self, job_id: str, limit: int = 10) -> List[Job]:
        """
        Find jobs similar to a given job using embeddings.
        
        Args:
            job_id: Source job ID
            limit: Maximum number of similar jobs
            
        Returns:
            List of similar jobs
        """
        
        # Get source job
        job_result = await self.db.execute(
            select(Job).where(Job.id == job_id)
        )
        source_job = job_result.scalar_one_or_none()
        
        if not source_job or not source_job.embedding:
            return []
        
        # Use pgvector to find similar jobs
        # This requires a custom SQL query with vector operations
        from sqlalchemy import text
        
        query = text("""
            SELECT id, title, company, 
                   embedding <-> :embedding as distance
            FROM jobseeker.jobs
            WHERE id != :job_id
              AND embedding IS NOT NULL
            ORDER BY distance
            LIMIT :limit
        """)
        
        result = await self.db.execute(
            query,
            {
                "embedding": source_job.embedding,
                "job_id": job_id,
                "limit": limit
            }
        )
        
        similar_job_ids = [row[0] for row in result.all()]
        
        # Fetch full job objects
        if similar_job_ids:
            jobs_result = await self.db.execute(
                select(Job).where(Job.id.in_(similar_job_ids))
            )
            return jobs_result.scalars().all()
        
        return []
    
    async def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context for scoring adjustments."""
        
        context = {}
        
        # Get recent positive feedback (applied/saved jobs)
        positive_feedback = await self.db.execute(
            select(UserFeedback)
            .where(
                and_(
                    UserFeedback.user_id == user_id,
                    UserFeedback.action.in_(["applied", "saved", "interviewed"])
                )
            )
            .order_by(desc(UserFeedback.created_at))
            .limit(20)
        )
        
        applied_job_ids = []
        for feedback in positive_feedback.scalars():
            if feedback.action == "applied":
                applied_job_ids.append(feedback.job_id)
        
        if applied_job_ids:
            applied_jobs_result = await self.db.execute(
                select(Job).where(Job.id.in_(applied_job_ids))
            )
            context["applied_jobs"] = [
                self._job_to_dict(job) 
                for job in applied_jobs_result.scalars()
            ]
        
        # Get recent negative feedback (rejected jobs)
        negative_feedback = await self.db.execute(
            select(UserFeedback)
            .where(
                and_(
                    UserFeedback.user_id == user_id,
                    UserFeedback.action == "rejected"
                )
            )
            .order_by(desc(UserFeedback.created_at))
            .limit(20)
        )
        
        rejected_job_ids = [f.job_id for f in negative_feedback.scalars()]
        
        if rejected_job_ids:
            rejected_jobs_result = await self.db.execute(
                select(Job).where(Job.id.in_(rejected_job_ids))
            )
            context["rejected_jobs"] = [
                self._job_to_dict(job)
                for job in rejected_jobs_result.scalars()
            ]
        
        return context
    
    def _job_to_dict(self, job: Job) -> Dict[str, Any]:
        """Convert Job model to dictionary for scoring."""
        
        return {
            "id": str(job.id),
            "title": job.title,
            "company": job.company,
            "description": job.description,
            "skills": job.skills or [],
            "requirements": job.requirements or [],
            "rate_min": job.rate_min,
            "rate_max": job.rate_max,
            "rate_type": job.rate_type,
            "location": job.location,
            "remote": job.remote,
            "hours_per_week": job.hours_per_week,
            "embedding": job.embedding
        }
    
    def _profile_to_dict(self, profile: UserProfile) -> Dict[str, Any]:
        """Convert UserProfile model to dictionary for scoring."""
        
        return {
            "id": str(profile.id),
            "skills": profile.skills or [],
            "experience_years": profile.experience_years,
            "certifications": profile.certifications or [],
            "preferences": profile.preferences or {},
            "min_rate_usd": profile.min_rate_usd,
            "max_hours_per_week": profile.max_hours_per_week,
            "availability": profile.availability or {},
            "portfolio": profile.portfolio or {},
            "profile_embedding": profile.profile_embedding
        }