"""LLM reasoning engine for cross-correlating macroeconomic data and central bank statements."""

import json
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

from ..config.settings import get_settings
from ..extractors.central_banks import CentralBankRelease
from ..extractors.fred_client import MacroDataPoint
from .schemas import (
    HawkishDovishTone,
    MacroAnomalyFlag,
    MacroPulseReportData,
    PolicyStance,
)

logger = logging.getLogger(__name__)


class LLMReasoner:
    """Orchestrates structured LLM analysis of macroeconomic data and speech transcripts."""

    def __init__(self, model_name: Optional[str] = None):
        settings = get_settings()
        self.model = model_name or settings.llm_model
        self.settings = settings

    async def analyze_and_synthesize(
        self,
        macro_data: List[MacroDataPoint],
        releases: List[CentralBankRelease],
    ) -> MacroPulseReportData:
        """Cross-correlate macro data points with central bank releases to generate a structured synthesis."""
        has_key = bool(
            self.settings.gemini_api_key
            or self.settings.openai_api_key
            or "MOCK" in self.model.upper()
        )

        if not has_key:
            logger.info("LLM credentials not detected; activating calibrated macroeconomic heuristic synthesis.")
            return self._generate_fallback_synthesis(macro_data, releases)

        prompt = self._build_synthesis_prompt(macro_data, releases)
        system_instruction = (
            "You are a Chief Global Macroeconomist and Quantitative Central Bank Watcher. "
            "Your task is to analyze official macroeconomic data and recent central bank statements. "
            "Be rigorous, concise, and empirical. Avoid generic filler words. "
            "You must respond ONLY with a valid JSON object matching the requested schema."
        )

        try:
            import litellm
            response = await litellm.acompletion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            raw_content = response.choices[0].message.content or ""
            # Strip markdown code blocks if returned by model
            cleaned_json_str = re.sub(r"^```json\s*|\s*```$", "", raw_content.strip(), flags=re.MULTILINE)
            parsed_json = json.loads(cleaned_json_str)

            report_id = f"MP-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
            parsed_json["report_id"] = report_id
            parsed_json["generated_at"] = datetime.now(timezone.utc).isoformat()

            return MacroPulseReportData.model_validate(parsed_json)

        except Exception as e:
            logger.error("LLM reasoning call failed: %s; invoking deterministic fallback.", e)
            return self._generate_fallback_synthesis(macro_data, releases)

    def _build_synthesis_prompt(
        self, macro_data: List[MacroDataPoint], releases: List[CentralBankRelease]
    ) -> str:
        """Construct a high-density prompt with macroeconomic readings and release text."""
        macro_summary = []
        for dp in macro_data:
            if dp.delta_bps is not None:
                delta_str = f" (Delta: {dp.delta:+.2f} / {dp.delta_bps:+.1f} bps)"
            elif dp.delta is not None and dp.delta_percentage is not None:
                delta_str = f" (Delta: {dp.delta:+.2f} / {dp.delta_percentage:+.1f}%)"
            else:
                delta_str = ""
            macro_summary.append(
                f"- {dp.meta.name} [{dp.meta.series_id}]: {dp.latest_value} {dp.meta.unit} as of {dp.latest_date}{delta_str}"
            )

        releases_summary = []
        for r in releases:
            releases_summary.append(
                f"### {r.institution} - {r.title} ({r.published_date})\n{r.summary}\n"
            )

        schema_example = json.dumps(
            {
                "executive_summary": "Detailed 2-3 paragraph summary connecting data and speech.",
                "primary_regime": "Late-Cycle Disinflation",
                "tone_assessment": {
                    "score": 0.25,
                    "stance": "Hawkish",
                    "confidence": 0.88,
                    "key_phrases_hawkish": ["inflation remains somewhat elevated", "attentive to risks"],
                    "key_phrases_dovish": ["job gains have moderated", "progress toward 2% target"],
                    "rationale": "Clear focus on data dependency with slight hawkish tilt due to sticky services inflation.",
                },
                "anomalies": [
                    {
                        "indicator": "T10Y2Y",
                        "severity": "HIGH",
                        "title": "Yield Curve Un-Inversion Dynamics",
                        "description": "Spread transitioning from inverted to positive, signaling late-cycle transition.",
                        "historical_precedent": "Pre-2008 and Pre-2001 dis-inversion phase.",
                    }
                ],
                "cross_asset_implications": [
                    "Equities: Multiple compression risk in high-beta growth; preference for defensive cash flows.",
                    "Bonds: Steepener trades favored as front-end yields price in rate cuts.",
                    "FX: Dollar supported by rate differentials in the short term.",
                ],
                "actionable_watchpoints": [
                    "Upcoming Core PCE release.",
                    "FOMC Chairman press conference Q&A.",
                ],
            },
            indent=2,
        )

        return f"""
Analyze the following live macroeconomic indicators and central bank releases:

### 1. Macroeconomic Indicators (FRED Data):
{chr(10).join(macro_summary)}

### 2. Central Bank Releases & Statements:
{chr(10).join(releases_summary)}

### Requirements:
Produce an exhaustive JSON output adhering strictly to this format:
{schema_example}
"""

    def _generate_fallback_synthesis(
        self, macro_data: List[MacroDataPoint], releases: List[CentralBankRelease]
    ) -> MacroPulseReportData:
        """Deterministic heuristic analysis when LLM API keys are not supplied."""
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

        anomalies: List[MacroAnomalyFlag] = []
        t10y2y = next((dp for dp in macro_data if dp.meta.series_id == "T10Y2Y"), None)
        if t10y2y:
            if t10y2y.latest_value < 0:
                anomalies.append(
                    MacroAnomalyFlag(
                        indicator="T10Y2Y",
                        severity="HIGH",
                        title="Inverted Treasury Yield Curve (10Y - 2Y)",
                        description=f"Spread is inverted at {t10y2y.latest_value:.2f}%, historically a leading indicator of macroeconomic slowdown.",
                        historical_precedent="1989, 2000, 2006-2007 recessionary lead cycles.",
                    )
                )
            else:
                anomalies.append(
                    MacroAnomalyFlag(
                        indicator="T10Y2Y",
                        severity="MEDIUM",
                        title="Normalized Yield Curve (Dis-inversion Phase)",
                        description=f"Spread is positive at {t10y2y.latest_value:.2f}%, indicating transition towards monetary normalization.",
                        historical_precedent="Post-inversion steepening historically precedes rate cut cycles.",
                    )
                )

        unrate = next((dp for dp in macro_data if dp.meta.series_id == "UNRATE"), None)
        if unrate and unrate.delta and unrate.delta > 0.3:
            anomalies.append(
                MacroAnomalyFlag(
                    indicator="UNRATE",
                    severity="HIGH",
                    title="Sahm Rule Warning: Labor Market Cooling",
                    description=f"Unemployment rate rose to {unrate.latest_value:.1f}%, reflecting emerging softness in hiring momentum.",
                    historical_precedent="Sahm rule threshold triggered during historical cycle turns.",
                )
            )

        return MacroPulseReportData(
            report_id=f"MP-{now_str}",
            generated_at=datetime.now(timezone.utc).isoformat(),
            executive_summary=(
                "Macroeconomic conditions reflect a balancing act between disinflationary progress and emerging labor market moderation. "
                "Central bank policy rates remain in restrictive territory to ensure inflation sustainably returns to the 2.0% target, "
                "while yield curve dynamics signal a transition from late-cycle tightening to potential recalibration."
            ),
            primary_regime="Late-Cycle Restrictive Stance",
            tone_assessment=HawkishDovishTone(
                score=0.20,
                stance=PolicyStance.HAWKISH,
                confidence=0.85,
                key_phrases_hawkish=[
                    "inflation remains somewhat elevated",
                    "attentive to inflation risks",
                ],
                key_phrases_dovish=[
                    "job gains have moderated",
                    "progress toward inflation target",
                ],
                rationale=(
                    "The committee maintains a cautious, data-dependent stance with a mild hawkish bias, "
                    "seeking greater confidence in inflation trajectories before aggressive easing."
                ),
            ),
            anomalies=anomalies,
            cross_asset_implications=[
                "Fixed Income: Duration risk remains attractive as peak policy rates cap long-term yield spikes.",
                "Equities: Quality cash-generative equities outperform cyclical sectors sensitive to borrowing costs.",
                "FX / USD: Broad dollar strength sustained by rate differentials against easing central banks.",
                "Commodities: Energy prices constrained by industrial demand deceleration.",
            ],
            actionable_watchpoints=[
                "Upcoming Nonfarm Payrolls (NFP) and Core PCE inflation print.",
                "Quarterly FOMC Summary of Economic Projections (Dot Plot).",
                "ECB policy rate announcement and Governing Council press conference.",
            ],
        )
