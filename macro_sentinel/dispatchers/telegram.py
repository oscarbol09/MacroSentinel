"""Telegram Bot alert dispatcher for real-time Macro Pulse notifications."""

import logging
from typing import Optional
import httpx
from ..analyzer.schemas import MacroPulseReportData
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class TelegramDispatcher:
    """Dispatches executive summaries to a Telegram channel or group."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        settings = get_settings()
        self.bot_token = bot_token or settings.telegram_bot_token
        self.chat_id = chat_id or settings.telegram_chat_id

    async def send_macro_pulse(self, report_data: MacroPulseReportData) -> bool:
        """Send a concise executive notification to the configured Telegram chat."""
        if not self.bot_token or not self.chat_id:
            logger.info("Telegram dispatcher not configured (missing bot token or chat ID). Skipping.")
            return False

        message = (
            f"🦅 *MacroSentinel: Macro Pulse Alert*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *Régimen:* `{report_data.primary_regime}`\n"
            f"🏛️ *Postura CB:* `{report_data.tone_assessment.stance.value}` (Score: `{report_data.tone_assessment.score:+.2f}`)\n\n"
            f"📝 *Resumen:*\n{report_data.executive_summary[:400]}...\n\n"
            f"🚨 *Anomalías:* {len(report_data.anomalies)} detectadas\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"_ID: {report_data.report_id}_"
        )

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(url, json=payload)
                res.raise_for_status()
                logger.info("Macro Pulse alert successfully dispatched to Telegram.")
                return True
            except Exception as e:
                logger.error(f"Failed to send Telegram alert: {e}")
                return False
