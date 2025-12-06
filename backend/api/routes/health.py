"""Health check endpoints."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from backend.database import get_db
from backend.config import settings

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.version,
        "environment": settings.environment,
    }


@router.get("/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check including database and Redis connectivity."""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.version,
        "environment": settings.environment,
        "checks": {}
    }
    
    # Check database connectivity
    try:
        result = await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
    
    # Check Redis connectivity
    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
    
    # Check ChromaDB connectivity
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{settings.chroma_host}:{settings.chroma_port}/api/v1/heartbeat",
                timeout=5.0
            )
            if response.status_code == 200:
                health_status["checks"]["chromadb"] = {
                    "status": "healthy",
                    "message": "ChromaDB connection successful"
                }
            else:
                raise Exception(f"ChromaDB returned status {response.status_code}")
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["chromadb"] = {
            "status": "unhealthy", 
            "message": f"ChromaDB connection failed: {str(e)}"
        }
    
    if health_status["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )
    
    return health_status


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Kubernetes readiness probe."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not ready"}
        )


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"status": "alive"}