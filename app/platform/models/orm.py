"""SQLAlchemy ORM table models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class GUID(TypeDecorator):
    """Platform-agnostic UUID column: uses PostgreSQL UUID on Postgres, String(36) elsewhere."""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=False))
        return dialect.type_descriptor(String(36))


class Base(DeclarativeBase):
    pass


class RunRecord(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    current_stage: Mapped[str] = mapped_column(String(50), default="theme_intake")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    checkpoint_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(100), nullable=True)


class CompanyRow(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(GUID(), nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    disposition: Mapped[str] = mapped_column(String(30), default="primary")
    ownership_tier: Mapped[str] = mapped_column(String(20), default="unknown")
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    eligible_for_outreach: Mapped[bool] = mapped_column(Boolean, default=False)
    workflow_stage: Mapped[str] = mapped_column(String(50), default="name_generation")
    review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    bizapi_status: Mapped[str] = mapped_column(String(20), default="pending")
    ciq_status: Mapped[str] = mapped_column(String(20), default="pending")
    bizapi_duns: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ciq_entity_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ThemeRecommendationRow(Base):
    __tablename__ = "theme_recommendations"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(GUID(), nullable=False, index=True)
    subvertical_name: Mapped[str] = mapped_column(String(300), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recommendation_status: Mapped[str] = mapped_column(String(30), default="watchlist")
    total_recommendation_score: Mapped[float] = mapped_column(Float, default=0.0)
    user_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    user_added: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SourceRecommendationRow(Base):
    __tablename__ = "source_recommendations"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(GUID(), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), default="")
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    user_selected: Mapped[bool] = mapped_column(Boolean, default=True)
    user_added: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CheckpointRow(Base):
    __tablename__ = "checkpoints"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(GUID(), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    company_count: Mapped[int] = mapped_column(Integer, default=0)
    artifact_path: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReviewQueueRow(Base):
    __tablename__ = "review_queue"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(GUID(), nullable=False, index=True)
    company_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExportManifestRow(Base):
    __tablename__ = "export_manifests"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(GUID(), nullable=False, index=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CompanyEvidenceRow(Base):
    """Raw connector outputs preserved separately from normalized company data."""

    __tablename__ = "company_evidence"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    company_id: Mapped[str] = mapped_column(GUID(), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(GUID(), nullable=False, index=True)
    connector_name: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ai_provenance: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
