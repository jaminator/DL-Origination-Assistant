"""Integration tests for database persistence using SQLite (async).

These tests verify ORM models, repositories, and session behavior
against a real SQL database (SQLite via aiosqlite).
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.platform.models.orm import Base
from app.platform.persistence.repositories import (
    CheckpointRepository,
    CompanyRepository,
    ExportRepository,
    RecommendationRepository,
    ReviewRepository,
    RunRepository,
)


@pytest.fixture
async def engine():
    """Create an in-memory SQLite async engine."""
    eng = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine):
    """Create an async session bound to the test engine."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


class TestSchemaCreation:
    """Verify all ORM tables are created correctly."""

    async def test_all_tables_exist(self, engine):
        from sqlalchemy import inspect

        async with engine.connect() as conn:
            table_names = await conn.run_sync(lambda c: inspect(c).get_table_names())
        expected = {
            "runs",
            "companies",
            "theme_recommendations",
            "source_recommendations",
            "checkpoints",
            "review_queue",
            "export_manifests",
            "company_evidence",
        }
        assert expected.issubset(set(table_names)), f"Missing tables: {expected - set(table_names)}"


class TestRunRepository:
    """Test RunRepository CRUD against real SQL."""

    async def test_create_run(self, session):
        repo = RunRepository(session)
        run = await repo.create({"theme": "data center capex"})
        assert run.id is not None
        assert run.config == {"theme": "data center capex"}
        assert run.status == "pending"
        assert run.current_stage == "theme_intake"

    async def test_get_run(self, session):
        repo = RunRepository(session)
        run = await repo.create({"theme": "test"})
        fetched = await repo.get(run.id)
        assert fetched is not None
        assert fetched.id == run.id
        assert fetched.config == {"theme": "test"}

    async def test_get_nonexistent_returns_none(self, session):
        repo = RunRepository(session)
        result = await repo.get(str(uuid4()))
        assert result is None

    async def test_update_stage(self, session):
        repo = RunRepository(session)
        run = await repo.create({"theme": "test"})
        await repo.update_stage(run.id, "name_generation", status="running")
        updated = await repo.get(run.id)
        assert updated.current_stage == "name_generation"
        assert updated.status == "running"

    async def test_update_status(self, session):
        repo = RunRepository(session)
        run = await repo.create({"theme": "test"})
        await repo.update_status(run.id, "completed")
        updated = await repo.get(run.id)
        assert updated.status == "completed"

    async def test_list_runs(self, session):
        repo = RunRepository(session)
        await repo.create({"theme": "run1"})
        await repo.create({"theme": "run2"})
        runs = await repo.list_runs()
        assert len(runs) == 2


class TestCompanyRepository:
    """Test CompanyRepository CRUD against real SQL."""

    async def test_upsert_and_get(self, session):
        repo = CompanyRepository(session)
        run_id = str(uuid4())
        company = await repo.upsert({
            "run_id": run_id,
            "canonical_name": "Acme Corp",
            "disposition": "primary",
            "ownership_tier": "founder_owned",
        })
        assert company.canonical_name == "Acme Corp"

        fetched = await repo.get(company.id)
        assert fetched is not None
        assert fetched.canonical_name == "Acme Corp"

    async def test_upsert_updates_existing(self, session):
        repo = CompanyRepository(session)
        run_id = str(uuid4())
        company_id = str(uuid4())
        await repo.upsert({
            "id": company_id,
            "run_id": run_id,
            "canonical_name": "Acme Corp",
            "disposition": "primary",
        })
        await repo.upsert({
            "id": company_id,
            "run_id": run_id,
            "canonical_name": "Acme Corp Updated",
            "disposition": "exclude",
        })
        fetched = await repo.get(company_id)
        assert fetched.canonical_name == "Acme Corp Updated"
        assert fetched.disposition == "exclude"

    async def test_list_by_run(self, session):
        repo = CompanyRepository(session)
        run_id = str(uuid4())
        await repo.upsert({"run_id": run_id, "canonical_name": "Alpha", "disposition": "primary"})
        await repo.upsert({"run_id": run_id, "canonical_name": "Beta", "disposition": "exclude"})
        await repo.upsert({"run_id": run_id, "canonical_name": "Gamma", "disposition": "primary"})

        all_companies = await repo.list_by_run(run_id)
        assert len(all_companies) == 3

        primary_only = await repo.list_by_run(run_id, disposition="primary")
        assert len(primary_only) == 2

    async def test_count_by_run(self, session):
        repo = CompanyRepository(session)
        run_id = str(uuid4())
        await repo.upsert({"run_id": run_id, "canonical_name": "A"})
        await repo.upsert({"run_id": run_id, "canonical_name": "B"})
        count = await repo.count_by_run(run_id)
        assert count == 2


class TestCheckpointRepository:
    """Test CheckpointRepository against real SQL."""

    async def test_create_and_get_latest(self, session):
        repo = CheckpointRepository(session)
        run_id = str(uuid4())
        await repo.create(run_id, "name_generation", 10, "/data/cp1.json")
        cp2 = await repo.create(run_id, "web_enhancement", 10, "/data/cp2.json")

        latest = await repo.get_latest(run_id)
        assert latest is not None
        assert latest.stage == "web_enhancement"
        assert latest.id == cp2.id

    async def test_list_by_run(self, session):
        repo = CheckpointRepository(session)
        run_id = str(uuid4())
        await repo.create(run_id, "stage1", 5, "/a")
        await repo.create(run_id, "stage2", 10, "/b")
        checkpoints = await repo.list_by_run(run_id)
        assert len(checkpoints) == 2
        assert checkpoints[0].stage == "stage1"

    async def test_get_latest_nonexistent(self, session):
        repo = CheckpointRepository(session)
        result = await repo.get_latest(str(uuid4()))
        assert result is None


class TestRecommendationRepository:
    """Test recommendation save/list against real SQL."""

    async def test_save_and_list_theme_recommendations(self, session):
        repo = RecommendationRepository(session)
        run_id = str(uuid4())
        recs = [
            {
                "run_id": run_id,
                "subvertical_name": "Data Center Cooling",
                "recommendation_status": "strong_fit",
                "total_recommendation_score": 85.0,
            },
            {
                "run_id": run_id,
                "subvertical_name": "Power Distribution",
                "recommendation_status": "moderate_fit",
                "total_recommendation_score": 60.0,
            },
        ]
        rows = await repo.save_theme_recommendations(recs)
        assert len(rows) == 2

        listed = await repo.list_theme_recommendations(run_id)
        assert len(listed) == 2
        assert listed[0].total_recommendation_score >= listed[1].total_recommendation_score

    async def test_update_selection(self, session):
        repo = RecommendationRepository(session)
        run_id = str(uuid4())
        rows = await repo.save_theme_recommendations([
            {"run_id": run_id, "subvertical_name": "Test", "total_recommendation_score": 50.0},
        ])
        assert rows[0].user_selected is False
        await repo.update_selection(rows[0].id, True)
        listed = await repo.list_theme_recommendations(run_id)
        assert listed[0].user_selected is True

    async def test_save_and_list_source_recommendations(self, session):
        repo = RecommendationRepository(session)
        run_id = str(uuid4())
        sources = [
            {"run_id": run_id, "source_name": "ENR Top 500", "source_type": "ranking_list"},
        ]
        rows = await repo.save_source_recommendations(sources)
        assert len(rows) == 1

        listed = await repo.list_source_recommendations(run_id)
        assert len(listed) == 1
        assert listed[0].source_name == "ENR Top 500"


class TestReviewRepository:
    """Test review queue against real SQL."""

    async def test_add_and_list(self, session):
        repo = ReviewRepository(session)
        run_id = str(uuid4())
        await repo.add({"run_id": run_id, "reason": "ambiguous_dedup", "details": "A vs A Inc"})
        await repo.add({"run_id": run_id, "reason": "qa_failure", "details": "unknown ownership"})

        items = await repo.list_by_run(run_id)
        assert len(items) == 2

        unresolved = await repo.list_by_run(run_id, resolved=False)
        assert len(unresolved) == 2

    async def test_resolve(self, session):
        repo = ReviewRepository(session)
        run_id = str(uuid4())
        item = await repo.add({"run_id": run_id, "reason": "ambiguous_dedup", "details": "test"})
        await repo.resolve(item.id, "merge")

        resolved = await repo.list_by_run(run_id, resolved=True)
        assert len(resolved) == 1
        assert resolved[0].resolution == "merge"


class TestExportRepository:
    """Test export manifest persistence."""

    async def test_save_and_list(self, session):
        repo = ExportRepository(session)
        run_id = str(uuid4())
        manifest = await repo.save_manifest({
            "run_id": run_id,
            "files": ["output.csv", "output.xlsx"],
            "company_count": 25,
        })
        assert manifest.id is not None

        listed = await repo.list_by_run(run_id)
        assert len(listed) == 1
        assert listed[0].data["company_count"] == 25


class TestCrossRepositoryWorkflow:
    """Test a realistic multi-repository workflow."""

    async def test_full_run_lifecycle(self, session):
        run_repo = RunRepository(session)
        company_repo = CompanyRepository(session)
        checkpoint_repo = CheckpointRepository(session)
        review_repo = ReviewRepository(session)
        export_repo = ExportRepository(session)

        # 1. Create run
        run = await run_repo.create({"theme": "data center capex"})
        assert run.status == "pending"

        # 2. Update to running
        await run_repo.update_status(run.id, "running")

        # 3. Add companies
        for name in ["Alpha Corp", "Beta Inc", "Gamma LLC"]:
            await company_repo.upsert({
                "run_id": run.id,
                "canonical_name": name,
                "disposition": "primary",
            })

        count = await company_repo.count_by_run(run.id)
        assert count == 3

        # 4. Save checkpoint
        cp = await checkpoint_repo.create(run.id, "name_generation", count, f"/data/{run.id}/cp.json")
        assert cp.company_count == 3

        # 5. Add review item
        await review_repo.add({
            "run_id": run.id,
            "reason": "ambiguous_dedup",
            "details": "Alpha Corp vs Alpha Corporation",
        })
        items = await review_repo.list_by_run(run.id, resolved=False)
        assert len(items) == 1

        # 6. Save export manifest
        manifest = await export_repo.save_manifest({
            "run_id": run.id,
            "files": ["output.csv"],
            "company_count": count,
        })
        assert manifest.data["company_count"] == 3

        # 7. Mark completed
        await run_repo.update_status(run.id, "completed")
        final = await run_repo.get(run.id)
        assert final.status == "completed"
