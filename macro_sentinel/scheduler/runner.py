"""Background worker engine and scheduler for periodic MacroSentinel runs."""

import asyncio
import logging
import traceback
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..analyzer.llm_reasoner import LLMReasoner
from ..config.settings import get_settings
from ..dispatchers.console import ConsoleDispatcher
from ..dispatchers.email import EmailDispatcher
from ..dispatchers.telegram import TelegramDispatcher
from ..extractors.bls_client import BLSClient
from ..extractors.central_banks import CentralBankExtractor
from ..extractors.cftc_client import CFTCClient
from ..extractors.fred_client import FredClient
from ..extractors.treasury_client import TreasuryClient
from ..reports.charts import ChartEngine
from ..reports.generator import ReportGenerator
from ..storage.quarantine import QuarantineStore
from ..storage.sqlite_cache import SQLiteCache

logger = logging.getLogger(__name__)


class SchedulerRunner:
    """Manages scheduled background scanning and report generation."""

    def __init__(self):
        self.settings = get_settings()
        self.fred_client = FredClient()
        self.treasury_client = TreasuryClient()
        self.bls_client = BLSClient()
        self.cftc_client = CFTCClient()
        self.cb_extractor = CentralBankExtractor()
        self.reasoner = LLMReasoner()
        self.report_generator = ReportGenerator()
        self.chart_engine = ChartEngine()
        self.console_dispatcher = ConsoleDispatcher()
        self.telegram_dispatcher = TelegramDispatcher()
        self.email_dispatcher = EmailDispatcher()
        self.cache = SQLiteCache()
        self.quarantine = QuarantineStore()
        self.scheduler = AsyncIOScheduler()

        self.circuit_breaker = {
            "FRED": {"failures": 0, "skip_runs": 0},
            "Treasury": {"failures": 0, "skip_runs": 0},
            "BLS": {"failures": 0, "skip_runs": 0},
            "CFTC": {"failures": 0, "skip_runs": 0},
        }

    async def _safe_extract(self, source_name: str, client: object, fetch_method: str) -> list:
        if self.circuit_breaker[source_name]["skip_runs"] > 0:
            logger.warning("Circuit breaker active for %s. Skipping this run.", source_name)
            self.circuit_breaker[source_name]["skip_runs"] -= 1
            return []

        try:
            async with client:
                data = await getattr(client, fetch_method)()
            self.circuit_breaker[source_name]["failures"] = 0
            return data
        except Exception as e:
            self.circuit_breaker[source_name]["failures"] += 1
            if self.circuit_breaker[source_name]["failures"] >= 3:
                self.circuit_breaker[source_name]["skip_runs"] = 3
                self.circuit_breaker[source_name]["failures"] = 0

            logger.warning("Source %s extraction failed: %s", source_name, e)
            self.quarantine.quarantine_failure(source_name, str(e), traceback.format_exc())
            return []

    async def execute_full_pipeline(self, render_to_console: bool = True) -> None:
        """Run the complete end-to-end macroeconomic intelligence pipeline."""
        start_time = datetime.now(timezone.utc)
        logger.info("Starting MacroSentinel pipeline execution...")

        try:
            # 1. Scatter-Gather macro data extraction
            logger.info("Fetching macroeconomic time series concurrently...")
            extract_tasks = [
                self._safe_extract("FRED", self.fred_client, "fetch_all_registered_series"),
                self._safe_extract("Treasury", self.treasury_client, "fetch_all_registered_series"),
                self._safe_extract("BLS", self.bls_client, "fetch_all_registered_series"),
                self._safe_extract("CFTC", self.cftc_client, "fetch_all_registered_series"),
            ]

            results = await asyncio.gather(*extract_tasks, return_exceptions=True)

            macro_data = []
            for res in results:
                if isinstance(res, Exception):
                    logger.warning("Unexpected extraction error: %s", res)
                elif isinstance(res, list):
                    macro_data.extend(res)

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

            # 7. Dispatch to Telegram and Email (if configured)
            await self.telegram_dispatcher.send_macro_pulse(report_data)
            await self.email_dispatcher.send_macro_digest(report_data, macro_data)

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
