"""Run configuration and context models."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.platform.models.enums import OwnershipTier, RunStatus, WorkflowStage


class RunConfig(BaseModel):
    """User-provided configuration for a single origination run."""

    # Theme
    theme: str
    theme_notes: str | None = None
    industry_description: str | None = None

    # Scope
    geography_filter: list[str] = Field(default_factory=lambda: ["US"])
    revenue_ceiling: float = 1000.0  # $1B in millions
    min_revenue_floor: float | None = None
    cascade_anchor_threshold: float = 1000.0
    ebitda_soft_ceiling: float = 150.0  # soft, NOT a hard exclude

    # Ownership
    ownership_tier_preference: list[OwnershipTier] = Field(
        default_factory=lambda: [OwnershipTier.TIER_A, OwnershipTier.TIER_B, OwnershipTier.TIER_C]
    )
    tier_a_scoring_bonus: float = 15.0
    tier_b_scoring_bonus: float = 8.0
    tier_c_scoring_bonus: float = 0.0

    # Workflow
    max_recursion_depth: int = 3
    include_cascade_anchors_in_outreach: bool = False
    boundary_treatment: str = "watch"
    outreach_list_size: int | None = None

    # Confirmed selections (populated during workflow)
    selected_subverticals: list[str] = Field(default_factory=list)
    selected_sources: list[dict] = Field(default_factory=list)
    naics_codes: list[str] = Field(default_factory=list)

    # Profile
    profile_name: str | None = None


class RunContext(BaseModel):
    """Runtime state for an active origination run."""

    id: UUID = Field(default_factory=uuid4)
    config: RunConfig
    current_stage: WorkflowStage = WorkflowStage.THEME_INTAKE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: RunStatus = RunStatus.PENDING
    checkpoint_id: UUID | None = None
    job_id: str | None = None


class CheckpointMetadata(BaseModel):
    """Metadata for a workflow checkpoint."""

    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    stage: WorkflowStage
    created_at: datetime = Field(default_factory=datetime.utcnow)
    company_count: int = 0
    artifact_path: str = ""
    notes: str | None = None
