"""Checkpoint save/load for workflow resumability."""

from datetime import datetime
from uuid import UUID, uuid4

from app.platform.persistence.storage import StorageBackend
from app.platform.utils.logging import get_logger

logger = get_logger("workflow.checkpoint")


class CheckpointManager:
    """Manages saving and loading workflow checkpoints."""

    def __init__(self, storage: StorageBackend):
        self._storage = storage

    async def save_checkpoint(
        self,
        run_id: UUID,
        stage: str,
        data: dict,
        company_count: int = 0,
        notes: str | None = None,
    ) -> dict:
        """Save a checkpoint after a stage completes."""
        checkpoint_id = str(uuid4())
        path = f"checkpoints/{run_id}/{stage}_{checkpoint_id}.json"

        payload = {
            "checkpoint_id": checkpoint_id,
            "run_id": str(run_id),
            "stage": stage,
            "company_count": company_count,
            "created_at": datetime.utcnow().isoformat(),
            "notes": notes,
            "data": data,
        }

        artifact_path = await self._storage.save_json(path, payload)
        logger.info("checkpoint_saved", run_id=str(run_id), stage=stage, path=artifact_path)

        return {
            "id": checkpoint_id,
            "run_id": str(run_id),
            "stage": stage,
            "company_count": company_count,
            "artifact_path": path,
            "notes": notes,
        }

    async def load_checkpoint(self, run_id: UUID, stage: str) -> dict | None:
        """Load the latest checkpoint for a given stage."""
        prefix = f"checkpoints/{run_id}/"
        files = await self._storage.list_files(prefix)
        stage_files = [f for f in files if f"/{stage}_" in f]

        if not stage_files:
            return None

        # Load the latest (by filename sort)
        latest = sorted(stage_files)[-1]
        return await self._storage.load_json(latest)
