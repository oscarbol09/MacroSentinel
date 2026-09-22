"""Telegram Bot alert dispatcher for real-time Macro Pulse notifications."""

import html
import logging
from typing import Optional
import httpx
from ..analyzer.schemas import MacroPulseReportData
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class TelegramDispatcher:
    """Dispatches executive summaries to a Telegram channel or group using safe HTML formatting."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        settings = get_settings()
        self.bot_token = bot_token or settings.telegram_bot_token
        self.chat_id = chat_id or settings.telegram_chat_id

    async def send_macro_pulse(self, report_data: MacroPulseReportData) -> bool:
        """Send a formatted executive notification to the configured Telegram chat."""
        if not self.bot_token or not self.chat_id:
            logger.info("Telegram dispatcher not configured (missing bot token or chat ID). Skipping.")
            return False

        safe_regime = html.escape(report_data.primary_regime)
        safe_stance = html.escape(report_data.tone_assessment.stance.value)
        safe_summary = html.escape(report_data.executive_summary[:350])

        message = (
            f"🦅 <b>MacroSentinel: Macro Pulse Alert</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>Régimen:</b> <code>{safe_regime}</code>\n"
            f"🏛️ <b>Postura CB:</b> <code>{safe_stance}</code> (Score: <code>{report_data.tone_assessment.score:+.2f}</code>)\n\n"
            f"📝 <b>Resumen:</b>\n<i>{safe_summary}...</i>\n\n"
            f"🚨 <b>Anomalías:</b> {len(report_data.anomalies)} detectadas\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<code>ID: {html.escape(report_data.report_id)}</code>"
        )

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(url, json=payload)
                res.raise_for_status()
                logger.info("Macro Pulse alert successfully dispatched to Telegram.")
                return True
            except Exception as e:
                logger.error("Failed to send Telegram alert: %s", e)
                return False
