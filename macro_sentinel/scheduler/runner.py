"""Background worker engine and scheduler for periodic MacroSentinel runs."""

import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..analyzer.llm_reasoner import LLMReasoner
from ..config.settings import get_settings
from ..dispatchers.console import ConsoleDispatcher
from ..dispatchers.telegram import TelegramDispatcher
from ..extractors.central_banks import CentralBankExtractor
from ..extractors.fred_client import FredClient
from ..reports.charts import ChartEngine
from ..reports.generator import ReportGenerator
from ..storage.sqlite_cache import SQLiteCache

logger = logging.getLogger(__name__)


class SchedulerRunner:
    """Manages scheduled background scanning and report generation."""

    def __init__(self):
        self.settings = get_settings()
        self.fred_client = FredClient()
        self.cb_extractor = CentralBankExtractor()
        self.reasoner = LLMReasoner()
        self.report_generator = ReportGenerator()
        self.chart_engine = ChartEngine()
        self.console_dispatcher = ConsoleDispatcher()
        self.telegram_dispatcher = TelegramDispatcher()
        self.cache = SQLiteCache()
        self.scheduler = AsyncIOScheduler()

    async def execute_full_pipeline(self, render_to_console: bool = True) -> None:
        """Run the complete end-to-end macroeconomic intelligence pipeline."""
        start_time = datetime.now(timezone.utc)
        logger.info("Starting MacroSentinel pipeline execution...")

        try:
            # 1. Ingest macroeconomic time series
            logger.info("Fetching macroeconomic time series from FRED API...")
            async with self.fred_client:
                macro_data = await self.fred_client.fetch_all_registered_series()

            # 2. Extract central bank releases
            logger.info("Extracting latest central bank releases and statements...")
            cb_releases = await self.cb_extractor.fetch_recent_releases()

            # 3. LLM Reasoning & Synthesis
            logger.info("Executing LLM reasoning for monetary tone and macro cycle dynamics...")
            report_data = await self.reasoner.analyze_and_synthesize(macro_data, cb_releases)

            # 4. Generate Visual Charts
            t10y2y_dp = next((dp for dp in macro_data if dp.meta.series_id == "T10Y2Y"), None)
            chart_path = None
            if t10y2y_dp:
                chart_path = self.chart_engine.generate_yield_curve_chart(t10y2y_dp, report_data.report_id)

            # 5. Render and Save Markdown Brief
            report_file = self.report_generator.generate_markdown_report(
                report_data, macro_data, chart_path=chart_path
            )
            logger.info("Macro Pulse report generated at %s", report_file)

            # 6. Record execution in SQLite Cache & Mark releases as processed
            self.cache.save_report(report_data, report_file)
            for r in cb_releases:
                content_hash = SQLiteCache.compute_content_hash(r.summary)
                self.cache.mark_release_processed(
                    url=r.link,
                    content_hash=content_hash,
                    institution=r.institution,
                    title=r.title,
                    published_date=r.published_date,
                )

            # 7. Dispatch to Telegram (if configured)
            await self.telegram_dispatcher.send_macro_pulse(report_data)

            # 8. Render to Console
            if render_to_console:
                self.console_dispatcher.render_report(report_data, macro_data)

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info("MacroSentinel pipeline successfully completed in %.2fs.", elapsed)

        except Exception as e:
            logger.error("MacroSentinel pipeline error: %s", e, exc_info=True)

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
            trigger = CronTrigger(minute=0, hour=8, day_of_week="mon-fri")

        self.scheduler.add_job(
            self.execute_full_pipeline,
            trigger=trigger,
            id="macrosentinel_daily_pulse",
            name="Daily Macro Pulse Scan",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("MacroSentinel daemon started with schedule: '%s'", self.settings.scan_cron_schedule)
