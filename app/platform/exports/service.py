"""Export orchestration — generates output files in multiple formats."""

from datetime import datetime
from uuid import UUID, uuid4

from app.platform.exports.csv_exporter import export_csv
from app.platform.exports.excel_exporter import export_excel
from app.platform.exports.json_exporter import export_json
from app.platform.persistence.storage import StorageBackend
from app.platform.utils.logging import get_logger

logger = get_logger("exports.service")


class ExportService:
    """Generates export files for a run."""

    def __init__(self, storage: StorageBackend):
        self._storage = storage

    async def export_run(
        self,
        run_id: UUID,
        companies: list[dict],
        format: str = "excel",
        config_snapshot: dict | None = None,
    ) -> dict:
        """Generate exports for a run. Returns export manifest."""
        logger.info("export_start", run_id=str(run_id), format=format, count=len(companies))

        manifest_id = str(uuid4())
        exports = []
        base_path = f"exports/{run_id}"

        if format in ("csv", "all"):
            path = f"{base_path}/master_universe.csv"
            csv_bytes = export_csv(companies)
            await self._storage.save(path, csv_bytes)
            exports.append({"name": "master_universe", "format": "csv", "path": path, "row_count": len(companies)})

        if format in ("json", "jsonl", "all"):
            path = f"{base_path}/master_universe.jsonl"
            json_bytes = export_json(companies)
            await self._storage.save(path, json_bytes)
            exports.append({"name": "master_universe", "format": "jsonl", "path": path, "row_count": len(companies)})

        if format in ("excel", "all"):
            path = f"{base_path}/origination_output.xlsx"
            excel_bytes = export_excel(companies)
            await self._storage.save(path, excel_bytes)
            exports.append({"name": "origination_output", "format": "xlsx", "path": path, "row_count": len(companies)})

        manifest = {
            "id": manifest_id,
            "run_id": str(run_id),
            "created_at": datetime.utcnow().isoformat(),
            "exports": exports,
            "config_snapshot": config_snapshot,
        }

        await self._storage.save_json(f"{base_path}/manifest.json", manifest)
        logger.info("export_complete", run_id=str(run_id), exports_count=len(exports))
        return manifest
