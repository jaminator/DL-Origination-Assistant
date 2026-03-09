"""AI confidence scoring and provenance framework."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AIProvenance(BaseModel):
    """Tracks the origin and confidence of AI-generated data."""

    ai_generated: bool = False
    model_source: str | None = None
    connector_source: str | None = None
    prompt_template_id: str | None = None
    prompt_template_version: str | None = None
    confidence_score: float | None = None
    supporting_evidence: list[str] = Field(default_factory=list)
    acceptance_status: str = "pending"  # pending | auto_accepted | human_accepted | human_rejected
    human_reviewed: bool = False
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    raw_response_ref: str | None = None

    def auto_accept(self, threshold: float) -> bool:
        """Check if this output should be auto-accepted based on confidence threshold."""
        if self.confidence_score is not None and self.confidence_score >= threshold:
            self.acceptance_status = "auto_accepted"
            return True
        return False

    def human_accept(self, reviewer: str | None = None) -> None:
        self.acceptance_status = "human_accepted"
        self.human_reviewed = True
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.utcnow()

    def human_reject(self, reviewer: str | None = None) -> None:
        self.acceptance_status = "human_rejected"
        self.human_reviewed = True
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.utcnow()


class ConnectorResult(BaseModel):
    """Standardized result from any AI/MCP connector."""

    raw_evidence: dict[str, Any] = Field(default_factory=dict)
    normalized_fields: dict[str, Any] = Field(default_factory=dict)
    ai_provenance: AIProvenance = Field(default_factory=AIProvenance)
    connector_name: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
