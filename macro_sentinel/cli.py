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

from .config.series_registry import (
    BLS_SERIES,
    CENTRAL_BANK_SOURCES,
    FRED_SERIES,
    TREASURY_ENDPOINTS,
)
from .extractors.bls_client import BLSClient
from .extractors.central_banks import CentralBankExtractor
from .extractors.cftc_client import CFTCClient
from .extractors.fred_client import FredClient
from .extractors.treasury_client import TreasuryClient
from .scheduler.runner import SchedulerRunner
from .storage.quarantine import QuarantineStore

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

    tr_table = Table(title="🏛️ U.S. Treasury Fiscal Data Endpoints", show_header=True)
    tr_table.add_column("Code", style="bold yellow")
    tr_table.add_column("Name")
    tr_table.add_column("Category", style="green")
    tr_table.add_column("Endpoint", style="dim")

    for tr in TREASURY_ENDPOINTS:
        tr_table.add_row(tr.code, tr.name, tr.category, tr.endpoint_path)

    console.print(tr_table)
    console.print()

    bls_table = Table(title="💼 Bureau of Labor Statistics (BLS) Series", show_header=True)
    bls_table.add_column("Series ID", style="bold blue")
    bls_table.add_column("Name")
    bls_table.add_column("Category", style="green")
    bls_table.add_column("Description", style="dim")

    for b in BLS_SERIES.values():
        bls_table.add_row(b.series_id, b.name, b.category, b.description)

    console.print(bls_table)
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
    """Test connectivity to external APIs (FRED, Treasury, BLS, CFTC, Central Banks)."""
    console.print("[cyan]Testing external API connectivity across all sources...[/cyan]")

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

        # 2. Test Treasury Fiscal Data
        console.print("[bold]2. Testing U.S. Treasury Fiscal Data API...[/bold]")
        tr_client = TreasuryClient()
        async with tr_client:
            try:
                rates = await tr_client.fetch_avg_interest_rates()
                console.print(f"  [green]✓[/green] Treasury (Avg Rate): {rates.latest_value}% ({rates.latest_date})")
            except Exception as e:
                console.print(f"  [red]✗[/red] Treasury API error: {e}")

        # 3. Test BLS
        console.print("[bold]3. Testing BLS API v2 Client...[/bold]")
        bls_client = BLSClient()
        async with bls_client:
            try:
                bls_data = await bls_client.fetch_series(["CUSR0000SA0"])
                if bls_data:
                    console.print(f"  [green]✓[/green] BLS (CPI-U): {bls_data[0].latest_value} ({bls_data[0].latest_date})")
            except Exception as e:
                console.print(f"  [red]✗[/red] BLS API error: {e}")

        # 4. Test CFTC
        console.print("[bold]4. Testing CFTC COT API Client...[/bold]")
        cftc_client = CFTCClient()
        async with cftc_client:
            try:
                cot_data = await cftc_client.fetch_positioning()
                if cot_data:
                    console.print(f"  [green]✓[/green] CFTC ({cot_data[0].contract_name[:30]}...): Net Pos = {cot_data[0].net_positioning:,.0f}")
            except Exception as e:
                console.print(f"  [red]✗[/red] CFTC API error: {e}")

        # 5. Test Central Banks
        console.print("[bold]5. Testing Central Bank Feeds...[/bold]")
        cb_ext = CentralBankExtractor()
        try:
            releases = await cb_ext.fetch_recent_releases(limit_per_source=1)
            for r in releases:
                console.print(f"  [green]✓[/green] {r.institution}: \"{r.title}\" ({r.published_date})")
        except Exception as e:
            console.print(f"  [red]✗[/red] Central bank extractor error: {e}")

    asyncio.run(_test())


@app.command()
def quarantine():
    """List currently quarantined failed extraction jobs."""
    store = QuarantineStore()
    items = store.get_quarantined_items()
    if not items:
        console.print("[green]✓ No quarantined pipeline failures detected.[/green]")
        return

    table = Table(title="⚠️ Quarantined Extraction Failures", show_header=True)
    table.add_column("ID", style="bold")
    table.add_column("Source", style="bold cyan")
    table.add_column("Error Message", style="red")
    table.add_column("Created At", style="dim")

    for item in items:
        table.add_row(
            str(item["id"]),
            item["source"],
            item["error_message"][:60] + ("..." if len(item["error_message"]) > 60 else ""),
            item["created_at"],
        )

    console.print(table)


if __name__ == "__main__":
    app()
