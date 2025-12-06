"""Embedding generation service for semantic matching."""

import asyncio
from typing import List, Optional, Dict, Any
import numpy as np
import logging

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from backend.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings for jobs and user profiles."""
    
    def __init__(self, model_type: str = "local"):
        """
        Initialize embedding service.
        
        Args:
            model_type: "local" for sentence-transformers, "openai" for OpenAI API
        """
        self.model_type = model_type
        
        if model_type == "local":
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                logger.warning("sentence-transformers not available, using mock embeddings")
                self.model = None
                self.dimension = 384
            else:
                # Use sentence-transformers for local embeddings
                self.model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dimensions
                self.dimension = 384
        elif model_type == "openai":
            # Use OpenAI embeddings
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            openai.api_key = settings.openai_api_key
            self.model = "text-embedding-ada-002"  # 1536 dimensions
            self.dimension = 1536
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    async def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        if not text:
            return np.zeros(self.dimension)
        
        if self.model_type == "local":
            return await self._generate_local_embedding(text)
        elif self.model_type == "openai":
            return await self._generate_openai_embedding(text)
    
    async def generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if self.model_type == "local":
            return await self._generate_local_embeddings(texts)
        elif self.model_type == "openai":
            # OpenAI supports batch processing
            tasks = [self._generate_openai_embedding(text) for text in texts]
            return await asyncio.gather(*tasks)
    
    async def _generate_local_embedding(self, text: str) -> np.ndarray:
        """Generate embedding using local sentence-transformers model."""
        if self.model is None:
            # Return mock embedding when model not available
            return np.random.randn(self.dimension).astype(np.float32)
        
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, 
                self.model.encode, 
                text,
                True  # normalize_embeddings
            )
            return embedding
        except Exception as e:
            logger.error(f"Error generating local embedding: {e}")
            return np.zeros(self.dimension)
    
    async def _generate_local_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts using local model."""
        if self.model is None:
            # Return mock embeddings when model not available
            return [np.random.randn(self.dimension).astype(np.float32) for _ in texts]
        
        try:
            # Batch processing for efficiency
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                self.model.encode,
                texts,
                None,  # convert_to_tensor
                32,    # batch_size
                True,  # show_progress_bar
                None,  # output_value
                True,  # normalize_embeddings
            )
            return list(embeddings)
        except Exception as e:
            logger.error(f"Error generating local embeddings: {e}")
            return [np.zeros(self.dimension) for _ in texts]
    
    async def _generate_openai_embedding(self, text: str) -> np.ndarray:
        """Generate embedding using OpenAI API."""
        try:
            # Clean and truncate text (OpenAI has token limits)
            text = text[:8000]  # Roughly 2000 tokens
            
            response = await asyncio.to_thread(
                openai.Embedding.create,
                input=text,
                model=self.model
            )
            
            embedding = response['data'][0]['embedding']
            return np.array(embedding)
            
        except Exception as e:
            logger.error(f"Error generating OpenAI embedding: {e}")
            return np.zeros(self.dimension)
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1
        """
        if embedding1.size == 0 or embedding2.size == 0:
            return 0.0
        
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        embedding1_norm = embedding1 / norm1
        embedding2_norm = embedding2 / norm2
        
        # Calculate cosine similarity
        similarity = np.dot(embedding1_norm, embedding2_norm)
        
        # Convert to 0-1 range
        return float((similarity + 1) / 2)
    
    async def generate_job_embedding(self, job: Dict[str, Any]) -> np.ndarray:
        """
        Generate embedding for a job posting.
        
        Args:
            job: Job data dictionary
            
        Returns:
            Embedding vector
        """
        # Combine relevant job fields for embedding
        text_parts = []
        
        if job.get('title'):
            text_parts.append(f"Title: {job['title']}")
        
        if job.get('company'):
            text_parts.append(f"Company: {job['company']}")
        
        if job.get('description'):
            # Limit description length
            desc = job['description'][:500]
            text_parts.append(f"Description: {desc}")
        
        if job.get('skills'):
            skills = ', '.join(job['skills']) if isinstance(job['skills'], list) else job['skills']
            text_parts.append(f"Skills: {skills}")
        
        if job.get('requirements'):
            reqs = job['requirements']
            if isinstance(reqs, list):
                reqs = ', '.join(reqs[:5])  # Limit to top 5
            text_parts.append(f"Requirements: {reqs}")
        
        if job.get('remote'):
            text_parts.append("Remote work")
        
        if job.get('rate_min') or job.get('rate_max'):
            rate_info = []
            if job.get('rate_min'):
                rate_info.append(f"${job['rate_min']}")
            if job.get('rate_max'):
                rate_info.append(f"${job['rate_max']}")
            if rate_info:
                rate_type = job.get('rate_type', 'hourly')
                text_parts.append(f"Rate: {'-'.join(rate_info)} {rate_type}")
        
        combined_text = ' | '.join(text_parts)
        return await self.generate_embedding(combined_text)
    
    async def generate_profile_embedding(self, profile: Dict[str, Any]) -> np.ndarray:
        """
        Generate embedding for a user profile.
        
        Args:
            profile: User profile data dictionary
            
        Returns:
            Embedding vector
        """
        # Combine relevant profile fields for embedding
        text_parts = []
        
        if profile.get('skills'):
            skills = ', '.join(profile['skills']) if isinstance(profile['skills'], list) else profile['skills']
            text_parts.append(f"Skills: {skills}")
        
        if profile.get('experience_years'):
            text_parts.append(f"Experience: {profile['experience_years']} years")
        
        if profile.get('certifications'):
            certs = profile['certifications']
            if isinstance(certs, list) and certs:
                text_parts.append(f"Certifications: {', '.join(certs)}")
        
        preferences = profile.get('preferences', {})
        
        if preferences.get('industries'):
            industries = ', '.join(preferences['industries'])
            text_parts.append(f"Preferred industries: {industries}")
        
        if preferences.get('remote_only'):
            text_parts.append("Remote work only")
        
        if profile.get('min_rate_usd'):
            text_parts.append(f"Minimum rate: ${profile['min_rate_usd']}/hour")
        
        if profile.get('portfolio'):
            portfolio = profile['portfolio']
            if portfolio.get('github'):
                text_parts.append(f"GitHub: {portfolio['github']}")
            if portfolio.get('website'):
                text_parts.append(f"Portfolio: {portfolio['website']}")
        
        # Add any specific job preferences
        if preferences.get('job_types'):
            job_types = ', '.join(preferences['job_types'])
            text_parts.append(f"Looking for: {job_types}")
        
        combined_text = ' | '.join(text_parts)
        return await self.generate_embedding(combined_text)