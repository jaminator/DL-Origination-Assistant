"""Typer CLI entrypoint for the DL Origination platform."""

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="dl-origination", help="Direct-lending origination target mining CLI")
console = Console()

# Sub-command groups
run_app = typer.Typer(help="Run management commands")
recommend_app = typer.Typer(help="Recommendation engine commands")
confirm_app = typer.Typer(help="Confirm selections")
mine_app = typer.Typer(help="Borrower miner commands")
review_app = typer.Typer(help="Review queue commands")
export_app = typer.Typer(help="Export commands")
connectors_app = typer.Typer(help="Connector management")

app.add_typer(run_app, name="run")
app.add_typer(recommend_app, name="recommend")
app.add_typer(confirm_app, name="confirm")
app.add_typer(mine_app, name="mine")
app.add_typer(review_app, name="review")
app.add_typer(export_app, name="export")
app.add_typer(connectors_app, name="connectors")


def _run_async(coro):
    return asyncio.run(coro)


async def _get_session():
    from app.platform.persistence.database import async_session
    async with async_session() as session:
        yield session


# ---- Run commands ----

@run_app.command("create")
def run_create(
    theme: str = typer.Option(..., help="Investment theme"),
    geography: str = typer.Option("US", help="Geography filter"),
    revenue_ceiling: float = typer.Option(1000.0, help="Revenue ceiling in $M"),
    profile: Optional[str] = typer.Option(None, help="Industry profile name"),
):
    """Create a new origination run."""
    async def _create():
        from app.platform.persistence.database import async_session, init_db
        from app.platform.persistence.repositories import RunRepository

        await init_db()
        async with async_session() as session:
            repo = RunRepository(session)
            config = {
                "theme": theme,
                "geography_filter": [geography],
                "revenue_ceiling": revenue_ceiling,
                "profile_name": profile,
            }
            run = await repo.create(config)
            console.print(f"[green]Run created:[/green] {run.id}")
            console.print(f"Theme: {theme}")
            console.print(f"Geography: {geography}")
            console.print(f"Revenue ceiling: ${revenue_ceiling}M")

    _run_async(_create())


@run_app.command("status")
def run_status(run_id: str = typer.Option(..., help="Run ID")):
    """Check run status."""
    async def _status():
        from app.platform.persistence.database import async_session
        from app.platform.persistence.repositories import RunRepository

        async with async_session() as session:
            repo = RunRepository(session)
            run = await repo.get(run_id)
            if not run:
                console.print("[red]Run not found[/red]")
                return
            table = Table(title=f"Run {run_id}")
            table.add_column("Field")
            table.add_column("Value")
            table.add_row("Status", run.status)
            table.add_row("Stage", run.current_stage)
            table.add_row("Created", run.created_at.isoformat())
            table.add_row("Theme", run.config.get("theme", ""))
            console.print(table)

    _run_async(_status())


@run_app.command("checkpoints")
def run_checkpoints(run_id: str = typer.Option(..., help="Run ID")):
    """List checkpoints for a run."""
    async def _checkpoints():
        from app.platform.persistence.database import async_session
        from app.platform.persistence.repositories import CheckpointRepository

        async with async_session() as session:
            repo = CheckpointRepository(session)
            cps = await repo.list_by_run(run_id)
            if not cps:
                console.print("[yellow]No checkpoints found[/yellow]")
                return
            table = Table(title=f"Checkpoints for {run_id}")
            table.add_column("ID")
            table.add_column("Stage")
            table.add_column("Companies")
            table.add_column("Created")
            for cp in cps:
                table.add_row(cp.id, cp.stage, str(cp.company_count), cp.created_at.isoformat())
            console.print(table)

    _run_async(_checkpoints())


# ---- Recommend commands ----

@recommend_app.command("subverticals")
def recommend_subverticals(run_id: str = typer.Option(..., help="Run ID")):
    """Generate sub-vertical recommendations."""
    async def _recommend():
        from uuid import UUID
        from app.ai.llm_service import get_llm_service
        from app.platform.persistence.database import async_session
        from app.platform.persistence.repositories import RecommendationRepository, RunRepository
        from app.platform.models.run import RunConfig
        from app.recommender.engine import RecommenderEngine

        async with async_session() as session:
            run_repo = RunRepository(session)
            run = await run_repo.get(run_id)
            if not run:
                console.print("[red]Run not found[/red]")
                return

            llm = get_llm_service()
            engine = RecommenderEngine(llm)
            config = RunConfig(**run.config)
            recs = await engine.recommend_subverticals(UUID(run_id), config)

            rec_repo = RecommendationRepository(session)
            rec_dicts = [r.model_dump(mode="json") for r in recs]
            for d in rec_dicts:
                d["run_id"] = run_id
            await rec_repo.save_theme_recommendations(rec_dicts)

            table = Table(title="Sub-vertical Recommendations")
            table.add_column("#", style="dim")
            table.add_column("Sub-vertical")
            table.add_column("Status")
            table.add_column("Thematic")
            table.add_column("Lender")
            table.add_column("Total")
            for i, r in enumerate(recs, 1):
                table.add_row(
                    str(i),
                    r.subvertical_name,
                    r.recommendation_status.value,
                    f"{r.thematic_fit_score:.0f}",
                    f"{r.lender_fit_score:.0f}",
                    f"{r.total_recommendation_score:.0f}",
                )
            console.print(table)

    _run_async(_recommend())


@recommend_app.command("sources")
def recommend_sources(run_id: str = typer.Option(..., help="Run ID")):
    """Generate source recommendations for confirmed sub-verticals."""
    async def _recommend():
        from uuid import UUID
        from app.ai.llm_service import get_llm_service
        from app.platform.persistence.database import async_session
        from app.platform.persistence.repositories import RecommendationRepository, RunRepository
        from app.recommender.engine import RecommenderEngine

        async with async_session() as session:
            run_repo = RunRepository(session)
            run = await run_repo.get(run_id)
            if not run:
                console.print("[red]Run not found[/red]")
                return

            # Get confirmed sub-verticals from run config
            selected = run.config.get("selected_subverticals", [])
            if not selected:
                # Fall back: use all theme recommendations
                rec_repo = RecommendationRepository(session)
                recs = await rec_repo.list_theme_recommendations(run_id)
                selected = [r.subvertical_name for r in recs]

            if not selected:
                console.print("[red]No sub-verticals selected. Run 'recommend subverticals' and 'confirm subverticals' first.[/red]")
                return

            llm = get_llm_service()
            engine = RecommenderEngine(llm)
            revenue_ceiling = run.config.get("revenue_ceiling", 1000.0)
            sources = await engine.recommend_sources(UUID(run_id), selected, revenue_ceiling)

            rec_repo = RecommendationRepository(session)
            src_dicts = [s.model_dump(mode="json") for s in sources]
            for d in src_dicts:
                d["run_id"] = run_id
            await rec_repo.save_source_recommendations(src_dicts)

            table = Table(title="Source Recommendations")
            table.add_column("#", style="dim")
            table.add_column("Source")
            table.add_column("Type")
            table.add_column("Sub-verticals")
            table.add_column("Priority")
            for i, s in enumerate(sources, 1):
                table.add_row(
                    str(i),
                    s.source_name,
                    s.source_type,
                    ", ".join(s.mapped_subverticals[:2]),
                    s.recommendation_priority.value,
                )
            console.print(table)

    _run_async(_recommend())


# ---- Confirm commands ----

@confirm_app.command("subverticals")
def confirm_subverticals(
    run_id: str = typer.Option(..., help="Run ID"),
    accept_all: bool = typer.Option(False, help="Accept all recommendations"),
    select: Optional[str] = typer.Option(None, help="Comma-separated indices to select (e.g., 1,3,5)"),
):
    """Confirm sub-vertical selections."""
    async def _confirm():
        from app.platform.persistence.database import async_session
        from app.platform.persistence.repositories import RecommendationRepository, RunRepository

        async with async_session() as session:
            rec_repo = RecommendationRepository(session)
            recs = await rec_repo.list_theme_recommendations(run_id)
            if not recs:
                console.print("[red]No recommendations found. Run 'recommend subverticals' first.[/red]")
                return

            if accept_all:
                selected_names = [r.subvertical_name for r in recs]
                for r in recs:
                    await rec_repo.update_selection(r.id, True)
            elif select:
                indices = [int(i.strip()) - 1 for i in select.split(",")]
                selected_names = []
                for i, r in enumerate(recs):
                    is_selected = i in indices
                    await rec_repo.update_selection(r.id, is_selected)
                    if is_selected:
                        selected_names.append(r.subvertical_name)
            else:
                console.print("[yellow]Specify --accept-all or --select indices[/yellow]")
                return

            # Save selections to run config
            run_repo = RunRepository(session)
            run = await run_repo.get(run_id)
            if run:
                run.config["selected_subverticals"] = selected_names
                await session.commit()

            console.print(f"[green]Confirmed {len(selected_names)} sub-verticals for run {run_id}[/green]")
            for name in selected_names:
                console.print(f"  - {name}")

    _run_async(_confirm())


@confirm_app.command("sources")
def confirm_sources(
    run_id: str = typer.Option(..., help="Run ID"),
    accept_all: bool = typer.Option(False, help="Accept all recommended sources"),
):
    """Confirm source selections."""
    async def _confirm():
        from app.platform.persistence.database import async_session
        from app.platform.persistence.repositories import RecommendationRepository, RunRepository

        async with async_session() as session:
            rec_repo = RecommendationRepository(session)
            sources = await rec_repo.list_source_recommendations(run_id)
            if not sources:
                console.print("[red]No source recommendations found. Run 'recommend sources' first.[/red]")
                return

            selected_sources = []
            for s in sources:
                src_data = s.data if isinstance(s.data, dict) else {}
                selected_sources.append({
                    "source_name": s.source_name,
                    "source_type": s.source_type,
                    "url": src_data.get("url"),
                    "subvertical": ", ".join(src_data.get("mapped_subverticals", [])),
                })

            run_repo = RunRepository(session)
            run = await run_repo.get(run_id)
            if run:
                run.config["selected_sources"] = selected_sources
                await session.commit()

            console.print(f"[green]Confirmed {len(selected_sources)} sources for run {run_id}[/green]")

    _run_async(_confirm())


# ---- Mine commands ----

@mine_app.command("execute")
def mine_execute(run_id: str = typer.Option(..., help="Run ID")):
    """Start the borrower mining pipeline."""
    async def _execute():
        from uuid import UUID
        from app.ai.llm_service import get_llm_service
        from app.miner.pitchbook.mcp_client import get_pitchbook_adapter
        from app.platform.persistence.database import async_session, init_db
        from app.platform.persistence.repositories import CompanyRepository, ReviewRepository, RunRepository
        from app.platform.persistence.storage import get_storage
        from app.miner.engine import MinerEngine

        await init_db()
        async with async_session() as session:
            run_repo = RunRepository(session)
            run = await run_repo.get(run_id)
            if not run:
                console.print("[red]Run not found[/red]")
                return

            llm = get_llm_service()
            pb = get_pitchbook_adapter()
            storage = get_storage()
            engine = MinerEngine(llm_service=llm, pitchbook_adapter=pb, storage=storage)

            console.print(f"[yellow]Starting pipeline for run {run_id}...[/yellow]")
            await run_repo.update_status(run_id, "running")

            try:
                results = await engine.execute_pipeline(UUID(run_id), run.config)

                # Persist companies to DB
                company_repo = CompanyRepository(session)
                for company in engine.companies:
                    await company_repo.upsert(company.model_dump(mode="json"))

                # Persist review items
                review_repo = ReviewRepository(session)
                for item in engine.review_items:
                    await review_repo.add(item.model_dump(mode="json"))

                await run_repo.update_status(run_id, "completed")
                console.print(f"[green]Pipeline complete![/green]")
                for stage, result in results.items():
                    console.print(f"  {stage}: {result.get('status', 'ok')}")
                console.print(f"  Total companies: {len(engine.companies)}")

            except Exception as e:
                await run_repo.update_status(run_id, "failed")
                console.print(f"[red]Pipeline failed: {e}[/red]")

    _run_async(_execute())


@mine_app.command("resume")
def mine_resume(run_id: str = typer.Option(..., help="Run ID")):
    """Resume pipeline from last checkpoint."""
    console.print(f"[yellow]Resume not yet supported from CLI. Use API: POST /api/v1/runs/{run_id}/resume[/yellow]")


@mine_app.command("rerun-stage")
def mine_rerun_stage(
    run_id: str = typer.Option(..., help="Run ID"),
    stage: str = typer.Option(..., help="Stage to re-run"),
):
    """Re-run a single pipeline stage."""
    async def _rerun():
        from uuid import UUID
        from app.ai.llm_service import get_llm_service
        from app.miner.pitchbook.mcp_client import get_pitchbook_adapter
        from app.platform.persistence.database import async_session, init_db
        from app.platform.persistence.repositories import RunRepository
        from app.platform.persistence.storage import get_storage
        from app.platform.models.enums import WorkflowStage
        from app.miner.engine import MinerEngine

        await init_db()
        async with async_session() as session:
            run_repo = RunRepository(session)
            run = await run_repo.get(run_id)
            if not run:
                console.print("[red]Run not found[/red]")
                return

            try:
                ws = WorkflowStage(stage)
            except ValueError:
                console.print(f"[red]Unknown stage: {stage}[/red]")
                console.print(f"Valid stages: {', '.join(s.value for s in WorkflowStage)}")
                return

            llm = get_llm_service()
            pb = get_pitchbook_adapter()
            storage = get_storage()
            engine = MinerEngine(llm_service=llm, pitchbook_adapter=pb, storage=storage)

            console.print(f"[yellow]Re-running stage {stage} for run {run_id}...[/yellow]")
            result = await engine.rerun_stage(UUID(run_id), run.config, ws)
            console.print(f"[green]Stage complete:[/green] {result}")

    _run_async(_rerun())


# ---- Review commands ----

@review_app.command("list")
def review_list(run_id: str = typer.Option(..., help="Run ID")):
    """List review queue items."""
    async def _list():
        from app.platform.persistence.database import async_session, init_db
        from app.platform.persistence.repositories import ReviewRepository

        await init_db()
        async with async_session() as session:
            repo = ReviewRepository(session)
            items = await repo.list_by_run(run_id, resolved=False)
            if not items:
                console.print("[green]No pending review items[/green]")
                return

            table = Table(title=f"Review Queue for {run_id}")
            table.add_column("ID")
            table.add_column("Reason")
            table.add_column("Details")
            table.add_column("Created")
            for item in items:
                table.add_row(
                    item.id[:8] + "...",
                    item.reason,
                    item.details[:60],
                    item.created_at.isoformat(),
                )
            console.print(table)

    _run_async(_list())


@review_app.command("resolve")
def review_resolve(
    item_id: str = typer.Option(..., help="Review item ID"),
    decision: str = typer.Option(..., help="Resolution: merge|keep_both|exclude|accept"),
):
    """Resolve a review queue item."""
    async def _resolve():
        from app.platform.persistence.database import async_session, init_db
        from app.platform.persistence.repositories import ReviewRepository

        await init_db()
        async with async_session() as session:
            repo = ReviewRepository(session)
            await repo.resolve(item_id, decision)
            console.print(f"[green]Resolved item {item_id} with decision: {decision}[/green]")

    _run_async(_resolve())


# ---- Export commands ----

@export_app.callback(invoke_without_command=True)
def export_run(
    run_id: str = typer.Option(..., help="Run ID"),
    format: str = typer.Option("excel", help="Export format: csv|json|excel|all"),
):
    """Export run results."""
    async def _export():
        from uuid import UUID
        from app.platform.persistence.database import async_session, init_db
        from app.platform.persistence.repositories import CompanyRepository
        from app.platform.persistence.storage import get_storage
        from app.platform.exports.service import ExportService

        await init_db()
        async with async_session() as session:
            company_repo = CompanyRepository(session)
            companies = await company_repo.list_by_run(run_id, limit=5000)
            if not companies:
                console.print("[yellow]No companies found for this run[/yellow]")
                return

            company_dicts = [c.data for c in companies]
            storage = get_storage()
            service = ExportService(storage)
            manifest = await service.export_run(UUID(run_id), company_dicts, format=format)

            console.print(f"[green]Export complete![/green]")
            for exp in manifest.get("exports", []):
                console.print(f"  {exp['format']}: {exp['path']} ({exp['row_count']} rows)")

    _run_async(_export())


# ---- Connector commands ----

@connectors_app.command("status")
def connectors_status():
    """Check connector health."""
    async def _status():
        from app.ai.mcp_manager import mcp_manager
        report = await mcp_manager.health_report()
        if not report:
            console.print("[yellow]No connectors registered[/yellow]")
            return
        table = Table(title="Connector Status")
        table.add_column("Connector")
        table.add_column("Available")
        table.add_column("Message")
        for name, health in report.items():
            status = "[green]Yes[/green]" if health.available else "[red]No[/red]"
            table.add_row(name, status, health.message)
        console.print(table)

    _run_async(_status())


if __name__ == "__main__":
    app()
