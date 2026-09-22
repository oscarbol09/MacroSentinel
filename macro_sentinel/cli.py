"""Command Line Interface (CLI) for MacroSentinel."""

import asyncio
import logging
import sys

import typer
from rich.console import Console
from rich.table import Table

# Ensure Windows terminal handles UTF-8 emojis without charmap encoding issues
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from .config.series_registry import CENTRAL_BANK_SOURCES, FRED_SERIES
from .extractors.central_banks import CentralBankExtractor
from .extractors.fred_client import FredClient
from .scheduler.runner import SchedulerRunner

app = typer.Typer(
    name="macro-sentinel",
    help="MacroSentinel: Autonomous Macroeconomic & Central Bank Intelligence Engine",
    add_completion=False,
)
console = Console(force_terminal=True, legacy_windows=False)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


@app.command()
def scan(
    now: bool = typer.Option(True, "--now", help="Execute the scan pipeline immediately."),
):
    """Run the complete macroeconomic intelligence pipeline and generate a Macro Pulse brief."""
    console.print("[bold cyan]🚀 Triggering MacroSentinel Pipeline...[/bold cyan]")
    runner = SchedulerRunner()
    asyncio.run(runner.execute_full_pipeline(render_to_console=True))


@app.command()
def daemon():
    """Start the MacroSentinel scheduler daemon in the foreground."""
    console.print("[bold green]⏱️ Starting MacroSentinel Scheduler Daemon...[/bold green]")
    runner = SchedulerRunner()
    runner.start_daemon()

    # Keep asyncio loop active
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        console.print("[yellow]Shutting down MacroSentinel Daemon...[/yellow]")
        runner.scheduler.shutdown()


@app.command()
def list_series():
    """List all registered macroeconomic indicators and central bank sources."""
    table = Table(title="📊 Registered Macroeconomic Time Series (FRED)", show_header=True)
    table.add_column("Series ID", style="bold cyan")
    table.add_column("Name")
    table.add_column("Category", style="green")
    table.add_column("Frequency")
    table.add_column("Description", style="dim")

    for s in FRED_SERIES.values():
        table.add_row(s.series_id, s.name, s.category, s.frequency, s.description)

    console.print(table)
    console.print()

    cb_table = Table(title="🏛️ Central Bank Communication Feeds", show_header=True)
    cb_table.add_column("Code", style="bold magenta")
    cb_table.add_column("Institution")
    cb_table.add_column("Type")
    cb_table.add_column("Feed URL", style="dim")

    for cb in CENTRAL_BANK_SOURCES:
        cb_table.add_row(cb.code, cb.institution, cb.feed_type, cb.feed_url)

    console.print(cb_table)


@app.command()
def test_apis():
    """Test connectivity to external APIs (FRED and Central Bank feeds)."""
    console.print("[cyan]Testing external API connectivity...[/cyan]")

    async def _test():
        # 1. Test FRED
        console.print("[bold]1. Testing FRED API Client...[/bold]")
        client = FredClient()
        async with client:
            try:
                dp = await client.fetch_series_observations("T10Y2Y", limit=3)
                console.print(f"  [green]✓[/green] FRED (T10Y2Y): Latest value = {dp.latest_value} ({dp.latest_date})")
            except Exception as e:
                console.print(f"  [red]✗[/red] FRED API error: {e}")

        # 2. Test Central Banks
        console.print("[bold]2. Testing Central Bank Feeds...[/bold]")
        cb_ext = CentralBankExtractor()
        try:
            releases = await cb_ext.fetch_recent_releases(limit_per_source=1)
            for r in releases:
                console.print(f"  [green]✓[/green] {r.institution}: \"{r.title}\" ({r.published_date})")
        except Exception as e:
            console.print(f"  [red]✗[/red] Central bank extractor error: {e}")

    asyncio.run(_test())


if __name__ == "__main__":
    app()
