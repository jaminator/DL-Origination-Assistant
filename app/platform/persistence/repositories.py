"""Repository pattern for database operations."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.models.orm import (
    CheckpointRow,
    CompanyEvidenceRow,
    CompanyRow,
    ExportManifestRow,
    ReviewQueueRow,
    RunRecord,
    SourceRecommendationRow,
    ThemeRecommendationRow,
)


class RunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, config: dict) -> RunRecord:
        run = RunRecord(id=str(uuid4()), config=config)
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get(self, run_id: str) -> RunRecord | None:
        result = await self.session.execute(select(RunRecord).where(RunRecord.id == run_id))
        return result.scalar_one_or_none()

    async def update_stage(self, run_id: str, stage: str, status: str | None = None) -> None:
        values: dict = {"current_stage": stage, "updated_at": datetime.utcnow()}
        if status:
            values["status"] = status
        await self.session.execute(update(RunRecord).where(RunRecord.id == run_id).values(**values))
        await self.session.commit()

    async def update_status(self, run_id: str, status: str) -> None:
        await self.session.execute(
            update(RunRecord).where(RunRecord.id == run_id).values(status=status, updated_at=datetime.utcnow())
        )
        await self.session.commit()

    async def list_runs(self, limit: int = 50) -> list[RunRecord]:
        result = await self.session.execute(select(RunRecord).order_by(RunRecord.created_at.desc()).limit(limit))
        return list(result.scalars().all())


class CompanyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, company_data: dict) -> CompanyRow:
        row = CompanyRow(
            id=company_data.get("id", str(uuid4())),
            run_id=company_data["run_id"],
            canonical_name=company_data["canonical_name"],
            data=company_data,
            disposition=company_data.get("disposition", "primary"),
            ownership_tier=company_data.get("ownership_tier", "unknown"),
            total_score=company_data.get("total_score"),
            eligible_for_outreach=company_data.get("eligible_for_outreach", False),
            workflow_stage=company_data.get("workflow_stage", "name_generation"),
            review_required=company_data.get("review_required", False),
        )
        merged = await self.session.merge(row)
        await self.session.commit()
        return merged

    async def get(self, company_id: str) -> CompanyRow | None:
        result = await self.session.execute(select(CompanyRow).where(CompanyRow.id == company_id))
        return result.scalar_one_or_none()

    async def list_by_run(
        self,
        run_id: str,
        disposition: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[CompanyRow]:
        q = select(CompanyRow).where(CompanyRow.run_id == run_id)
        if disposition:
            q = q.where(CompanyRow.disposition == disposition)
        q = q.order_by(CompanyRow.canonical_name).limit(limit).offset(offset)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def count_by_run(self, run_id: str) -> int:
        from sqlalchemy import func

        result = await self.session.execute(select(func.count()).where(CompanyRow.run_id == run_id))
        return result.scalar_one()


class CheckpointRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, run_id: str, stage: str, company_count: int, artifact_path: str, notes: str | None = None) -> CheckpointRow:
        row = CheckpointRow(
            id=str(uuid4()),
            run_id=run_id,
            stage=stage,
            company_count=company_count,
            artifact_path=artifact_path,
            notes=notes,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def get_latest(self, run_id: str) -> CheckpointRow | None:
        result = await self.session.execute(
            select(CheckpointRow).where(CheckpointRow.run_id == run_id).order_by(CheckpointRow.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_run(self, run_id: str) -> list[CheckpointRow]:
        result = await self.session.execute(
            select(CheckpointRow).where(CheckpointRow.run_id == run_id).order_by(CheckpointRow.created_at.asc())
        )
        return list(result.scalars().all())


class RecommendationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_theme_recommendations(self, recommendations: list[dict]) -> list[ThemeRecommendationRow]:
        rows = []
        for rec in recommendations:
            row = ThemeRecommendationRow(
                id=rec.get("id", str(uuid4())),
                run_id=rec["run_id"],
                subvertical_name=rec["subvertical_name"],
                data=rec,
                recommendation_status=rec.get("recommendation_status", "watchlist"),
                total_recommendation_score=rec.get("total_recommendation_score", 0.0),
                user_selected=rec.get("user_selected", False),
                user_added=rec.get("user_added", False),
            )
            self.session.add(row)
            rows.append(row)
        await self.session.commit()
        return rows

    async def list_theme_recommendations(self, run_id: str) -> list[ThemeRecommendationRow]:
        result = await self.session.execute(
            select(ThemeRecommendationRow)
            .where(ThemeRecommendationRow.run_id == run_id)
            .order_by(ThemeRecommendationRow.total_recommendation_score.desc())
        )
        return list(result.scalars().all())

    async def update_selection(self, recommendation_id: str, user_selected: bool) -> None:
        await self.session.execute(
            update(ThemeRecommendationRow)
            .where(ThemeRecommendationRow.id == recommendation_id)
            .values(user_selected=user_selected)
        )
        await self.session.commit()

    async def save_source_recommendations(self, sources: list[dict]) -> list[SourceRecommendationRow]:
        rows = []
        for src in sources:
            row = SourceRecommendationRow(
                id=src.get("id", str(uuid4())),
                run_id=src["run_id"],
                source_name=src["source_name"],
                source_type=src.get("source_type", ""),
                data=src,
                user_selected=src.get("user_selected", True),
                user_added=src.get("user_added", False),
            )
            self.session.add(row)
            rows.append(row)
        await self.session.commit()
        return rows

    async def list_source_recommendations(self, run_id: str) -> list[SourceRecommendationRow]:
        result = await self.session.execute(
            select(SourceRecommendationRow).where(SourceRecommendationRow.run_id == run_id)
        )
        return list(result.scalars().all())


class ReviewRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, item: dict) -> ReviewQueueRow:
        row = ReviewQueueRow(
            id=item.get("id", str(uuid4())),
            run_id=item["run_id"],
            company_id=item.get("company_id"),
            reason=item["reason"],
            details=item.get("details", ""),
            data=item,
        )
        self.session.add(row)
        await self.session.commit()
        return row

    async def list_by_run(self, run_id: str, resolved: bool | None = None) -> list[ReviewQueueRow]:
        q = select(ReviewQueueRow).where(ReviewQueueRow.run_id == run_id)
        if resolved is not None:
            q = q.where(ReviewQueueRow.resolved == resolved)
        result = await self.session.execute(q.order_by(ReviewQueueRow.created_at.asc()))
        return list(result.scalars().all())

    async def resolve(self, item_id: str, resolution: str) -> None:
        await self.session.execute(
            update(ReviewQueueRow)
            .where(ReviewQueueRow.id == item_id)
            .values(resolved=True, resolution=resolution, resolved_at=datetime.utcnow())
        )
        await self.session.commit()


class ExportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_manifest(self, manifest: dict) -> ExportManifestRow:
        row = ExportManifestRow(
            id=manifest.get("id", str(uuid4())),
            run_id=manifest["run_id"],
            data=manifest,
        )
        self.session.add(row)
        await self.session.commit()
        return row

    async def list_by_run(self, run_id: str) -> list[ExportManifestRow]:
        result = await self.session.execute(
            select(ExportManifestRow).where(ExportManifestRow.run_id == run_id).order_by(ExportManifestRow.created_at.desc())
        )
        return list(result.scalars().all())
