"""Configuration settings for the JobSeeker AI application."""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Application
    app_name: str = "JobSeeker AI"
    version: str = "0.1.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Security
    secret_key: str = Field(env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080,http://localhost:8081,http://192.168.1.160:8080,http://192.168.1.160:8081,http://10.0.2.2:8080,http://10.0.2.2:8081",
        validation_alias="ALLOWED_ORIGINS"
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        """Get allowed origins as a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
    
    # Database
    database_url: str = Field(env="DATABASE_URL")
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    
    # Redis
    redis_url: str = Field(env="REDIS_URL")
    
    # ChromaDB
    chroma_host: str = Field(default="localhost", env="CHROMA_HOST")
    chroma_port: int = Field(default=8000, env="CHROMA_PORT")
    
    # AI/ML Services
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")

    # LLM Configuration
    llm_provider: str = Field(default="ollama", env="LLM_PROVIDER")  # ollama, openai, anthropic
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", env="OLLAMA_MODEL")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    anthropic_model: str = Field(default="claude-3-haiku-20240307", env="ANTHROPIC_MODEL")

    # Demo Mode (for local development without auth/payments)
    demo_mode: bool = Field(default=True, env="DEMO_MODE")
    
    # Email Configuration
    email_imap_server: str = Field(default="imap.gmail.com", env="EMAIL_IMAP_SERVER")
    email_imap_port: int = Field(default=993, env="EMAIL_IMAP_PORT")
    email_address: Optional[str] = Field(default=None, env="EMAIL_ADDRESS")
    email_password: Optional[str] = Field(default=None, env="EMAIL_PASSWORD")
    
    # SMTP Configuration
    smtp_server: str = Field(default="smtp.gmail.com", env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    
    # Slack Integration
    slack_bot_token: Optional[str] = Field(default=None, env="SLACK_BOT_TOKEN")
    slack_app_token: Optional[str] = Field(default=None, env="SLACK_APP_TOKEN")
    slack_signing_secret: Optional[str] = Field(default=None, env="SLACK_SIGNING_SECRET")
    
    # AWS Configuration
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    aws_s3_bucket: Optional[str] = Field(default=None, env="AWS_S3_BUCKET")
    
    # Job Processing Settings
    max_jobs_per_digest: int = Field(default=10, env="MAX_JOBS_PER_DIGEST")
    job_score_threshold: float = Field(default=70.0, env="JOB_SCORE_THRESHOLD")
    proposal_max_length: int = Field(default=200, env="PROPOSAL_MAX_LENGTH")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=3600, env="RATE_LIMIT_PERIOD")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")

    # Stripe Configuration
    stripe_secret_key: Optional[str] = Field(default=None, env="STRIPE_SECRET_KEY")
    stripe_publishable_key: Optional[str] = Field(default=None, env="STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: Optional[str] = Field(default=None, env="STRIPE_WEBHOOK_SECRET")

    # Stripe Price IDs (set these in Stripe dashboard)
    stripe_price_starter: Optional[str] = Field(default=None, env="STRIPE_PRICE_STARTER")
    stripe_price_pro: Optional[str] = Field(default=None, env="STRIPE_PRICE_PRO")
    stripe_price_power: Optional[str] = Field(default=None, env="STRIPE_PRICE_POWER")

    @property
    def stripe_configured(self) -> bool:
        """Check if Stripe is properly configured."""
        return bool(self.stripe_secret_key and self.stripe_publishable_key)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from .env
    )


# Global settings instance
settings = Settings()