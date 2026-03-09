"""Tests for WorkflowOrchestrator with DB persistence and checkpointing."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.ai.llm_service import MockLLMService
from app.miner.engine import MinerEngine
from app.miner.pitchbook.mock_client import MockPitchBookClient
from app.miner.sources.registry import SourceRegistry
from app.platform.persistence.storage import LocalStorage
from app.platform.workflow.orchestrator import WorkflowOrchestrator


@pytest.fixture
def run_id():
    return uuid4()


@pytest.fixture
def run_config():
    return {
        "theme": "data center capex secular growth",
        "geography_filter": ["US"],
        "revenue_ceiling": 1000.0,
        "cascade_anchor_threshold": 1000.0,
        "tier_a_scoring_bonus": 15.0,
        "tier_b_scoring_bonus": 8.0,
        "tier_c_scoring_bonus": 0.0,
        "selected_sources": [
            {"source_name": "Test Source", "source_type": "ranking_list"},
        ],
    }


@pytest.fixture
def mock_run_repo(run_config):
    repo = AsyncMock()
    run = MagicMock()
    run.config = run_config
    run.id = str(uuid4())
    repo.get.return_value = run
    return repo


@pytest.fixture
def mock_company_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_review_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_checkpoint_repo():
    repo = AsyncMock()
    repo.get_latest.return_value = None
    return repo


@pytest.fixture
def miner(tmp_path):
    return MinerEngine(
        llm_service=MockLLMService(),
        pitchbook_adapter=MockPitchBookClient(),
        storage=LocalStorage(str(tmp_path)),
        source_registry=SourceRegistry(use_mock=True),
    )


@pytest.mark.asyncio
async def test_orchestrator_run_pipeline(
    run_id, miner, mock_run_repo, mock_company_repo, mock_review_repo, mock_checkpoint_repo,
):
    """Orchestrator should run pipeline and persist results."""
    orchestrator = WorkflowOrchestrator(
        run_repo=mock_run_repo,
        checkpoint_repo=mock_checkpoint_repo,
        company_repo=mock_company_repo,
        review_repo=mock_review_repo,
    )

    result = await orchestrator.run_pipeline(run_id, miner_engine=miner)

    # Pipeline should have completed
    assert result is not None
    assert len(result) == 10

    # Run status should have been updated
    mock_run_repo.update_status.assert_called()
    mock_run_repo.update_stage.assert_called()

    # Companies should have been persisted
    assert mock_company_repo.upsert.call_count > 0

    # Checkpoint should have been saved
    assert mock_checkpoint_repo.create.call_count > 0


@pytest.mark.asyncio
async def test_orchestrator_persists_companies(
    run_id, miner, mock_run_repo, mock_company_repo, mock_review_repo, mock_checkpoint_repo,
):
    """Orchestrator should persist all discovered companies."""
    orchestrator = WorkflowOrchestrator(
        run_repo=mock_run_repo,
        checkpoint_repo=mock_checkpoint_repo,
        company_repo=mock_company_repo,
        review_repo=mock_review_repo,
    )

    await orchestrator.run_pipeline(run_id, miner_engine=miner)

    # Each company should have been upserted
    company_count = mock_company_repo.upsert.call_count
    assert company_count > 0
    assert company_count == len(miner.companies)


@pytest.mark.asyncio
async def test_orchestrator_marks_completed(
    run_id, miner, mock_run_repo, mock_company_repo, mock_review_repo, mock_checkpoint_repo,
):
    """Orchestrator should mark run as completed."""
    orchestrator = WorkflowOrchestrator(
        run_repo=mock_run_repo,
        checkpoint_repo=mock_checkpoint_repo,
        company_repo=mock_company_repo,
        review_repo=mock_review_repo,
    )

    await orchestrator.run_pipeline(run_id, miner_engine=miner)

    # Should have been marked as completed
    mock_run_repo.update_stage.assert_called_with(str(run_id), "completed", "completed")


@pytest.mark.asyncio
async def test_orchestrator_handles_failure(
    run_id, mock_run_repo, mock_company_repo, mock_review_repo, mock_checkpoint_repo,
):
    """Orchestrator should mark run as failed on error."""
    # Create a mock miner that will fail
    miner = MagicMock()
    miner.execute_pipeline = AsyncMock(side_effect=RuntimeError("test failure"))
    miner.companies = []
    miner.review_items = []

    orchestrator = WorkflowOrchestrator(
        run_repo=mock_run_repo,
        checkpoint_repo=mock_checkpoint_repo,
        company_repo=mock_company_repo,
        review_repo=mock_review_repo,
    )

    with pytest.raises(RuntimeError):
        await orchestrator.run_pipeline(run_id, miner_engine=miner)

    mock_run_repo.update_status.assert_any_call(str(run_id), "failed")
