"""ML model tracking and versioning."""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.sql import func

from backend.database import Base


class MLModel(Base):
    """ML model tracking for versioning and A/B testing."""
    
    __tablename__ = "ml_models"
    __table_args__ = (
        UniqueConstraint("model_name", "version", name="uq_model_name_version"),
        {"schema": "jobseeker"}
    )
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Model identification
    model_name = Column(String(100), nullable=False, index=True)
    model_type = Column(String(50), nullable=False, index=True)
    # Types: "scoring", "embedding", "proposal", "bandit"
    
    version = Column(String(50), nullable=False)  # "v1.0", "2024-01-15", etc.
    
    # Model configuration
    parameters = Column(JSONB, nullable=False, default=dict)
    # Contains: hyperparameters, feature weights, etc.
    
    # Performance metrics
    metrics = Column(JSONB, nullable=False, default=dict) 
    # Contains: accuracy, precision, recall, etc.
    
    # Model storage
    file_path = Column(Text)  # Path to model file (S3, local, etc.)
    
    # Status
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    @property
    def accuracy(self) -> Optional[float]:
        """Get model accuracy if available."""
        return self.metrics.get("accuracy")
    
    @property
    def precision(self) -> Optional[float]:
        """Get model precision if available."""
        return self.metrics.get("precision")
    
    @property
    def recall(self) -> Optional[float]:
        """Get model recall if available."""
        return self.metrics.get("recall")
    
    @property
    def f1_score(self) -> Optional[float]:
        """Get model F1 score if available."""
        return self.metrics.get("f1_score")
    
    def update_metrics(self, new_metrics: Dict) -> None:
        """Update model performance metrics."""
        self.metrics = {**self.metrics, **new_metrics}
    
    def activate(self) -> None:
        """Activate this model version."""
        self.is_active = True
    
    def deactivate(self) -> None:
        """Deactivate this model version."""
        self.is_active = False
    
    @classmethod
    def create_scoring_model(
        cls,
        version: str,
        parameters: Dict,
        file_path: Optional[str] = None,
        metrics: Optional[Dict] = None
    ) -> "MLModel":
        """Create a new scoring model version."""
        
        return cls(
            model_name="job_scorer",
            model_type="scoring",
            version=version,
            parameters=parameters,
            file_path=file_path,
            metrics=metrics or {}
        )
    
    @classmethod
    def create_bandit_model(
        cls,
        version: str,
        parameters: Dict,
        metrics: Optional[Dict] = None
    ) -> "MLModel":
        """Create a new bandit model version."""
        
        return cls(
            model_name="thompson_sampling_bandit",
            model_type="bandit",
            version=version,
            parameters=parameters,
            metrics=metrics or {}
        )