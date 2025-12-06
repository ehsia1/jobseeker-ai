"""Service for generating and managing embeddings."""

import logging
import numpy as np
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
import hashlib
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import asyncio

from backend.models.job import Job
from backend.models.user import UserProfile

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings for jobs and profiles."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding service.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Initialized embedding model {model_name} with dimension {self.embedding_dim}")
        
        # Cache for embeddings to avoid recomputation
        self._embedding_cache = {}
        self._cache_size_limit = 1000
    
    def generate_text_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        # Check cache first
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        # Generate embedding
        embedding = self.model.encode(text, convert_to_numpy=True)
        
        # Cache it (with size limit)
        if len(self._embedding_cache) < self._cache_size_limit:
            self._embedding_cache[cache_key] = embedding
        
        return embedding
    
    def generate_job_embedding(self, job: Dict[str, Any]) -> np.ndarray:
        """
        Generate embedding for a job.
        
        Args:
            job: Job dictionary
            
        Returns:
            Embedding vector for the job
        """
        # Combine relevant job fields into a single text
        job_text_parts = []
        
        # Title is most important
        if job.get('title'):
            job_text_parts.append(f"Title: {job['title']}")
        
        # Company provides context
        if job.get('company'):
            job_text_parts.append(f"Company: {job['company']}")
        
        # Description is the main content
        if job.get('description'):
            # Limit description length to avoid token limits
            description = job['description'][:2000]
            job_text_parts.append(f"Description: {description}")
        
        # Skills are crucial for matching
        if job.get('skills'):
            skills_text = ", ".join(job['skills']) if isinstance(job['skills'], list) else str(job['skills'])
            job_text_parts.append(f"Required Skills: {skills_text}")
        
        # Requirements
        if job.get('requirements'):
            req_text = json.dumps(job['requirements']) if isinstance(job['requirements'], dict) else str(job['requirements'])
            job_text_parts.append(f"Requirements: {req_text[:500]}")
        
        # Location and remote status
        if job.get('location'):
            job_text_parts.append(f"Location: {job['location']}")
        if job.get('remote'):
            job_text_parts.append("Remote: Yes")
        
        # Combine all parts
        job_text = "\n".join(job_text_parts)
        
        return self.generate_text_embedding(job_text)
    
    def generate_profile_embedding(self, profile: UserProfile) -> np.ndarray:
        """
        Generate embedding for a user profile.
        
        Args:
            profile: UserProfile object
            
        Returns:
            Embedding vector for the profile
        """
        profile_text_parts = []
        
        # Profession and job title
        if profile.profession:
            profile_text_parts.append(f"Profession: {profile.profession}")
        if profile.job_title:
            profile_text_parts.append(f"Current/Desired Role: {profile.job_title}")
        
        # Skills are most important
        if profile.skills:
            skills_text = ", ".join(profile.skills) if isinstance(profile.skills, list) else str(profile.skills)
            profile_text_parts.append(f"Skills: {skills_text}")
        
        # Experience
        if profile.experience:
            profile_text_parts.append(f"Experience: {profile.experience[:1000]}")
        elif profile.experience_years:
            profile_text_parts.append(f"Years of Experience: {profile.experience_years}")
        
        # Education and certifications
        if profile.education:
            profile_text_parts.append(f"Education: {profile.education}")
        if profile.certifications:
            certs_text = ", ".join(profile.certifications) if isinstance(profile.certifications, list) else str(profile.certifications)
            profile_text_parts.append(f"Certifications: {certs_text}")
        
        # Preferences
        if profile.preferences:
            if profile.preferences.get('remote_only'):
                profile_text_parts.append("Prefers remote work")
            if profile.preferences.get('industries'):
                industries = ", ".join(profile.preferences['industries'])
                profile_text_parts.append(f"Preferred Industries: {industries}")
        
        # Location
        if profile.location:
            profile_text_parts.append(f"Location: {profile.location}")
        
        # Combine all parts
        profile_text = "\n".join(profile_text_parts)
        
        return self.generate_text_embedding(profile_text)
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1
        """
        # Normalize vectors
        norm1 = embedding1 / np.linalg.norm(embedding1)
        norm2 = embedding2 / np.linalg.norm(embedding2)
        
        # Calculate cosine similarity
        similarity = np.dot(norm1, norm2)
        
        # Convert to 0-1 range (cosine similarity is -1 to 1)
        return float((similarity + 1) / 2)
    
    async def update_job_embeddings(self, db: AsyncSession, jobs: List[Job]) -> int:
        """
        Update embeddings for a list of jobs.
        
        Args:
            db: Database session
            jobs: List of Job objects
            
        Returns:
            Number of jobs updated
        """
        updated_count = 0
        
        for job in jobs:
            try:
                # Generate embedding
                job_dict = {
                    'title': job.title,
                    'company': job.company,
                    'description': job.description,
                    'skills': job.skills,
                    'requirements': job.requirements,
                    'location': job.location,
                    'remote': job.remote
                }
                embedding = self.generate_job_embedding(job_dict)
                
                # Convert to list for storage
                embedding_list = embedding.tolist()
                
                # Update job with embedding
                await db.execute(
                    update(Job)
                    .where(Job.id == job.id)
                    .values(embedding=embedding_list)
                )
                
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error generating embedding for job {job.id}: {e}")
                continue
        
        await db.commit()
        logger.info(f"Updated embeddings for {updated_count} jobs")
        return updated_count
    
    async def update_profile_embedding(self, db: AsyncSession, profile: UserProfile) -> bool:
        """
        Update embedding for a user profile.
        
        Args:
            db: Database session
            profile: UserProfile object
            
        Returns:
            True if successful
        """
        try:
            # Generate embedding
            embedding = self.generate_profile_embedding(profile)
            
            # Convert to list for storage
            embedding_list = embedding.tolist()
            
            # Update profile with embedding
            await db.execute(
                update(UserProfile)
                .where(UserProfile.id == profile.id)
                .values(profile_embedding=embedding_list)
            )
            
            await db.commit()
            logger.info(f"Updated embedding for profile {profile.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating profile embedding: {e}")
            return False
    
    async def find_similar_jobs(
        self, 
        db: AsyncSession, 
        reference_embedding: np.ndarray,
        limit: int = 10,
        min_similarity: float = 0.5
    ) -> List[tuple[Job, float]]:
        """
        Find jobs similar to a reference embedding.
        
        Args:
            db: Database session
            reference_embedding: Reference embedding to compare against
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of (job, similarity_score) tuples
        """
        # Get jobs with embeddings
        result = await db.execute(
            select(Job).where(Job.embedding.isnot(None)).limit(100)
        )
        jobs = result.scalars().all()
        
        # Calculate similarities
        similar_jobs = []
        for job in jobs:
            if job.embedding:
                job_embedding = np.array(job.embedding)
                similarity = self.calculate_similarity(reference_embedding, job_embedding)
                
                if similarity >= min_similarity:
                    similar_jobs.append((job, similarity))
        
        # Sort by similarity and return top results
        similar_jobs.sort(key=lambda x: x[1], reverse=True)
        return similar_jobs[:limit]
    
    def calculate_skill_overlap(self, job_skills: List[str], profile_skills: List[str]) -> float:
        """
        Calculate skill overlap between job and profile.
        
        Args:
            job_skills: List of job required skills
            profile_skills: List of user skills
            
        Returns:
            Overlap score between 0 and 1
        """
        if not job_skills or not profile_skills:
            return 0.0
        
        # Convert to lowercase sets for comparison
        job_set = set(s.lower() for s in job_skills)
        profile_set = set(s.lower() for s in profile_skills)
        
        # Calculate Jaccard similarity
        intersection = len(job_set & profile_set)
        union = len(job_set | profile_set)
        
        if union == 0:
            return 0.0
        
        return intersection / union