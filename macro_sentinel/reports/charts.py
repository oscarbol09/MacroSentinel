"""Financial chart generator using Matplotlib in headless mode."""

import logging
from pathlib import Path
from typing import Optional
import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend for background services
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

from ..config.settings import get_settings
from ..extractors.fred_client import MacroDataPoint

logger = logging.getLogger(__name__)


class ChartEngine:
    """Renders financial charts for inclusion in Macro Pulse briefs and dispatchers."""

    def __init__(self, figures_dir: Optional[Path] = None):
        settings = get_settings()
        self.figures_dir = figures_dir or (settings.data_storage_dir / "reports" / "figures")
        self.figures_dir.mkdir(parents=True, exist_ok=True)

    def generate_yield_curve_chart(
        self, t10y2y_point: MacroDataPoint, report_id: str
    ) -> Optional[Path]:
        """Plot the 10Y - 2Y Treasury Yield Spread history with inversion zone highlighting."""
        if not t10y2y_point.observations:
            return None

        # Sort observations chronologically
        obs_sorted = sorted(t10y2y_point.observations, key=lambda x: x.date)
        dates = []
        values = []
        for obs in obs_sorted:
            try:
                dates.append(datetime.strptime(obs.date, "%Y-%m-%d"))
                values.append(obs.value)
            except ValueError:
                continue

        if not dates:
            return None

        file_name = f"yield_curve_{report_id}.png"
        output_path = self.figures_dir / file_name

        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(9, 4.5), dpi=150)

        # Plot spread line
        ax.plot(dates, values, color="#00d2ff", linewidth=2.0, label="10Y - 2Y Spread (T10Y2Y)")
        ax.axhline(0, color="#ff4b4b", linestyle="--", linewidth=1.2, alpha=0.8, label="Inversion Threshold (0.00%)")

        # Fill inversion zones (< 0%) and normalization zones (>= 0%)
        ax.fill_between(
            dates,
            values,
            0,
            where=[v < 0 for v in values],
            color="#ff4b4b",
            alpha=0.25,
            interpolate=True,
            label="Inverted (Recession Signal)",
        )
        ax.fill_between(
            dates,
            values,
            0,
            where=[v >= 0 for v in values],
            color="#00e676",
            alpha=0.15,
            interpolate=True,
            label="Normal / Dis-inversion",
        )

        # Latest point annotation
        latest_val = values[-1]
        latest_date = dates[-1]
        ax.scatter([latest_date], [latest_val], color="#ffffff", s=50, zorder=5)
        ax.annotate(
            f"Latest: {latest_val:+.2f}%",
            xy=(latest_date, latest_val),
            xytext=(10, 10),
            textcoords="offset points",
            color="#ffffff",
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="#1e293b", ec="#00d2ff", lw=1.2),
        )

        ax.set_title("Treasury Yield Curve Spread (10-Year minus 2-Year)", fontsize=12, fontweight="bold", pad=12, color="#f1f5f9")
        ax.set_ylabel("Yield Spread (%)", fontsize=10, color="#cbd5e1")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.grid(True, linestyle=":", alpha=0.3, color="#64748b")
        ax.legend(loc="upper left", framealpha=0.6, fontsize=8)

        fig.tight_layout()
        fig.savefig(output_path, format="png", bbox_inches="tight")
        plt.close(fig)

        logger.info("Yield curve chart generated at %s", output_path)
        return output_path
