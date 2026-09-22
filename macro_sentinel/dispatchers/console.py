"""Rich console rendering for CLI executions and interactive dashboards."""

import sys
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..analyzer.schemas import MacroPulseReportData
from ..extractors.fred_client import MacroDataPoint


class ConsoleDispatcher:
    """Renders MacroSentinel telemetry and executive reports to the console."""

    def __init__(self):
        if sys.platform == "win32":
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except AttributeError:
                pass
        self.console = Console(force_terminal=True, legacy_windows=False)

    def render_report(
        self, report_data: MacroPulseReportData, macro_points: List[MacroDataPoint]
    ) -> None:
        """Print an aesthetic financial terminal dashboard."""
        self.console.print()
        self.console.rule("[bold cyan]🦅 MacroSentinel — Macro Pulse Intelligence Brief[/bold cyan]")
        self.console.print()

        # Regime & Tone Panel
        score = report_data.tone_assessment.score
        score_color = "red" if score > 0.2 else ("green" if score < -0.2 else "yellow")
        stance_str = f"[{score_color}]{report_data.tone_assessment.stance.value} ({score:+.2f})[/{score_color}]"

        header_text = Text.from_markup(
            f"[bold]Report ID:[/bold] {report_data.report_id}  |  [bold]Regime:[/bold] [magenta]{report_data.primary_regime}[/magenta]\n"
            f"[bold]Central Bank Stance:[/bold] {stance_str} (Confianza: {report_data.tone_assessment.confidence * 100:.0f}%)\n"
            f"[dim]{report_data.tone_assessment.rationale}[/dim]"
        )
        self.console.print(Panel(header_text, title="🎯 Monetary Policy & Macro State", border_style="cyan"))

        # Executive Summary Panel
        self.console.print(
            Panel(
                f"[italic]{report_data.executive_summary}[/italic]",
                title="📝 Resumen Ejecutivo",
                border_style="bright_blue",
            )
        )

        # Macro Indicators Table
        table = Table(title="📈 Macroeconomic Indicators Dashboard (FRED Data)", show_header=True, header_style="bold magenta")
        table.add_column("Indicator", style="bold")
        table.add_column("Category")
        table.add_column("Latest Value", justify="right")
        table.add_column("Delta", justify="right")
        table.add_column("As of Date", justify="center")

        for dp in macro_points:
            delta_str = "—"
            if dp.delta is not None and dp.delta_percentage is not None:
                color = "green" if dp.delta >= 0 else "red"
                delta_str = f"[{color}]{dp.delta:+.2f} ({dp.delta_percentage:+.1f}%)[/{color}]"

            table.add_row(
                f"{dp.meta.name} ({dp.meta.series_id})",
                dp.meta.category,
                f"{dp.latest_value:.2f} {dp.meta.unit}",
                delta_str,
                dp.latest_date,
            )

        self.console.print(table)
        self.console.print()

        # Anomalies Panel if any
        if report_data.anomalies:
            anomaly_lines = []
            for a in report_data.anomalies:
                severity_color = "red" if a.severity in ("HIGH", "CRITICAL") else "yellow"
                anomaly_lines.append(
                    f"[bold {severity_color}]• [{a.severity}] {a.title} ({a.indicator}):[/bold {severity_color}]\n"
                    f"  {a.description}\n"
                    + (f"  [dim]Precedente: {a.historical_precedent}[/dim]\n" if a.historical_precedent else "")
                )
            self.console.print(
                Panel("\n".join(anomaly_lines), title="🚨 Anomalías y Señales de Riesgo", border_style="red")
            )

        # Cross-Asset Panel
        cross_lines = [f"[bold green]•[/bold green] {item}" for item in report_data.cross_asset_implications]
        self.console.print(
            Panel("\n".join(cross_lines), title="💼 Implicaciones por Clase de Activo", border_style="green")
        )

        # Watchpoints
        watch_lines = [f"[bold yellow]⏱️[/bold yellow] {item}" for item in report_data.actionable_watchpoints]
        self.console.print(
            Panel("\n".join(watch_lines), title="🔭 Catalizadores a Vigilar (Watchpoints)", border_style="yellow")
        )
        self.console.rule()
        self.console.print()
