"""
Free-tier optimized configuration for JobSeeker AI
Designed to run at $0 cost while scaling to thousands of users
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class FreeT ierSettings(BaseSettings):
    """Configuration optimized for free hosting tiers"""
    
    # Application
    app_name: str = "JobSeeker AI"
    version: str = "1.0.0"
    environment: str = Field(default="production", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Database (Supabase or Render PostgreSQL)
    database_url: str = Field(env="DATABASE_URL")
    # Use connection pooling to stay within free connection limits
    database_pool_size: int = Field(default=5, env="DB_POOL_SIZE")  # Supabase free: 60 connections
    database_max_overflow: int = Field(default=10, env="DB_MAX_OVERFLOW")
    
    # Redis (Upstash - 10K commands/day free)
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    cache_ttl_hours: int = Field(default=6, env="CACHE_TTL_HOURS")  # Aggressive caching
    cache_enabled: bool = Field(default=True, env="CACHE_ENABLED")
    
    # Security
    secret_key: str = Field(env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # CORS
    allowed_origins_str: str = Field(
        default="http://localhost:3000,https://*.vercel.app",
        env="ALLOWED_ORIGINS"
    )
    
    @property
    def allowed_origins(self):
        return [origin.strip() for origin in self.allowed_origins_str.split(",")]
    
    # Rate Limiting (preserve free tier limits)
    rate_limit_enabled: bool = Field(default=True, env="ENABLE_RATE_LIMIT")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=3600, env="RATE_LIMIT_PERIOD")
    
    # Job Search Optimization
    max_jobs_per_search: int = Field(default=50, env="MAX_JOBS_PER_SEARCH")
    batch_search_interval: int = Field(default=1800, env="BATCH_SEARCH_INTERVAL")  # 30 minutes
    enable_client_scoring: bool = Field(default=True, env="ENABLE_CLIENT_SCORING")
    
    # Free Tier Optimizations
    use_memory_cache: bool = Field(default=True, env="USE_MEMORY_CACHE")
    compress_responses: bool = Field(default=True, env="COMPRESS_RESPONSES")
    pagination_default_size: int = Field(default=20, env="PAGINATION_SIZE")
    max_request_size_mb: int = Field(default=1, env="MAX_REQUEST_SIZE_MB")
    
    # Optional Premium Features (disabled by default)
    enable_email_notifications: bool = Field(default=False, env="ENABLE_EMAIL")
    enable_websockets: bool = Field(default=False, env="ENABLE_WEBSOCKETS")
    enable_background_jobs: bool = Field(default=False, env="ENABLE_BACKGROUND_JOBS")
    
    # Monitoring (free tiers)
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")  # Free: 5K events/month
    enable_metrics: bool = Field(default=False, env="ENABLE_METRICS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Initialize settings
settings = FreeT ierSettings()


# Free tier limits reference
FREE_TIER_LIMITS = {
    "supabase": {
        "database_size": "500MB",
        "bandwidth": "2GB",
        "auth_users": 50000,
        "edge_functions": "500K invocations",
        "storage": "1GB",
        "connections": 60
    },
    "render": {
        "hours_per_month": 750,
        "bandwidth": "100GB",
        "memory": "512MB",
        "builds_per_month": 400,
        "auto_sleep_after": "15 minutes inactivity"
    },
    "vercel": {
        "bandwidth": "100GB",
        "serverless_execution": "100GB-hours",
        "edge_requests": "1M",
        "builds_per_day": 100
    },
    "upstash_redis": {
        "commands_per_day": 10000,
        "storage": "256MB",
        "bandwidth": "256MB"
    },
    "cloudflare": {
        "requests": "unlimited",
        "bandwidth": "unlimited",
        "workers": "100K requests/day",
        "kv_operations": "100K reads/day"
    }
}