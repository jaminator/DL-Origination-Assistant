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
    """Generate source recommendations."""
    console.print(f"[yellow]Generating source recommendations for run {run_id}...[/yellow]")
    # TODO: Wire up similar to subverticals


# ---- Confirm commands ----

@confirm_app.command("subverticals")
def confirm_subverticals(
    run_id: str = typer.Option(..., help="Run ID"),
    accept_all: bool = typer.Option(False, help="Accept all recommendations"),
    select: Optional[str] = typer.Option(None, help="Comma-separated indices to select (e.g., 1,3,5)"),
):
    """Confirm sub-vertical selections."""
    console.print(f"[green]Sub-verticals confirmed for run {run_id}[/green]")
    # TODO: Wire up to repository


@confirm_app.command("sources")
def confirm_sources(
    run_id: str = typer.Option(..., help="Run ID"),
    accept_all: bool = typer.Option(False, help="Accept all recommended sources"),
):
    """Confirm source selections."""
    console.print(f"[green]Sources confirmed for run {run_id}[/green]")


# ---- Mine commands ----

@mine_app.command("execute")
def mine_execute(run_id: str = typer.Option(..., help="Run ID")):
    """Start the borrower mining pipeline."""
    console.print(f"[yellow]Starting pipeline for run {run_id}...[/yellow]")
    # TODO: Wire up to job enqueue


@mine_app.command("resume")
def mine_resume(run_id: str = typer.Option(..., help="Run ID")):
    """Resume pipeline from last checkpoint."""
    console.print(f"[yellow]Resuming pipeline for run {run_id}...[/yellow]")


@mine_app.command("rerun-stage")
def mine_rerun_stage(
    run_id: str = typer.Option(..., help="Run ID"),
    stage: str = typer.Option(..., help="Stage to re-run"),
):
    """Re-run a single pipeline stage."""
    console.print(f"[yellow]Re-running stage {stage} for run {run_id}...[/yellow]")


# ---- Review commands ----

@review_app.command("list")
def review_list(run_id: str = typer.Option(..., help="Run ID")):
    """List review queue items."""
    console.print(f"[yellow]Listing review items for run {run_id}...[/yellow]")


@review_app.command("resolve")
def review_resolve(
    item_id: str = typer.Option(..., help="Review item ID"),
    decision: str = typer.Option(..., help="Resolution: merge|keep_both|exclude|accept"),
):
    """Resolve a review queue item."""
    console.print(f"[green]Resolved item {item_id} with decision: {decision}[/green]")


# ---- Export commands ----

@export_app.callback(invoke_without_command=True)
def export_run(
    run_id: str = typer.Option(..., help="Run ID"),
    format: str = typer.Option("excel", help="Export format: csv|json|excel|all"),
):
    """Export run results."""
    console.print(f"[yellow]Exporting run {run_id} as {format}...[/yellow]")


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
