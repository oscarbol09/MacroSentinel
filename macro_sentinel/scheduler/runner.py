"""Background worker engine and scheduler for periodic MacroSentinel runs."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..analyzer.llm_reasoner import LLMReasoner
from ..config.settings import get_settings
from ..dispatchers.console import ConsoleDispatcher
from ..dispatchers.telegram import TelegramDispatcher
from ..extractors.central_banks import CentralBankExtractor
from ..extractors.fred_client import FredClient
from ..reports.generator import ReportGenerator

logger = logging.getLogger(__name__)


class SchedulerRunner:
    """Manages scheduled background scanning and report generation."""

    def __init__(self):
        self.settings = get_settings()
        self.fred_client = FredClient()
        self.cb_extractor = CentralBankExtractor()
        self.reasoner = LLMReasoner()
        self.report_generator = ReportGenerator()
        self.console_dispatcher = ConsoleDispatcher()
        self.telegram_dispatcher = TelegramDispatcher()
        self.scheduler = AsyncIOScheduler()

    async def execute_full_pipeline(self, render_to_console: bool = True) -> None:
        """Run the complete end-to-end macroeconomic intelligence pipeline."""
        start_time = datetime.now(timezone.utc)
        logger.info("Starting MacroSentinel pipeline execution...")

        try:
            # 1. Ingest FRED macro time series
            logger.info("Fetching macroeconomic time series from FRED API...")
            async with self.fred_client:
                macro_data = await self.fred_client.fetch_all_registered_series()

            # 2. Extract Central Bank statements
            logger.info("Extracting latest central bank releases and statements...")
            cb_releases = await self.cb_extractor.fetch_recent_releases()

            # 3. LLM Reasoning & Synthesis
            logger.info("Executing LLM reasoning for Hawkish-Dovish tone and macro correlations...")
            report_data = await self.reasoner.analyze_and_synthesize(macro_data, cb_releases)

            # 4. Generate Markdown Artifact
            report_file = self.report_generator.generate_markdown_report(report_data, macro_data)
            logger.info(f"Macro Pulse report generated: {report_file}")

            # 5. Dispatch to Telegram (if configured)
            await self.telegram_dispatcher.send_macro_pulse(report_data)

            # 6. Render to Console
            if render_to_console:
                self.console_dispatcher.render_report(report_data, macro_data)

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"MacroSentinel pipeline successfully completed in {elapsed:.2f}s.")

        except Exception as e:
            logger.error(f"MacroSentinel pipeline error: {e}", exc_info=True)

    def start_daemon(self) -> None:
        """Start the background scheduler daemon."""
        cron_expr = self.settings.scan_cron_schedule.split()
        if len(cron_expr) == 5:
            trigger = CronTrigger(
                minute=cron_expr[0],
                hour=cron_expr[1],
                day=cron_expr[2],
                month=cron_expr[3],
                day_of_week=cron_expr[4],
            )
        else:
            # Default to weekdays at 8:00 AM
            trigger = CronTrigger(minute=0, hour=8, day_of_week="mon-fri")

        self.scheduler.add_job(
            self.execute_full_pipeline,
            trigger=trigger,
            id="macrosentinel_daily_pulse",
            name="Daily Macro Pulse Scan",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info(f"MacroSentinel daemon started. Schedule: '{self.settings.scan_cron_schedule}'")
