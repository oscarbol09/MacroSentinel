"""Client for the Federal Reserve Bank of St. Louis (FRED) API."""

import logging
from datetime import datetime, timezone
from typing import List, Optional
import httpx
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config.series_registry import FRED_SERIES, MacroSeriesMeta
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class SeriesObservation(BaseModel):
    """Single data observation from a FRED time series."""
    date: str
    value: float


class MacroDataPoint(BaseModel):
    """Structured container for a series and its most recent observations."""
    meta: MacroSeriesMeta
    latest_value: float
    previous_value: Optional[float] = None
    delta: Optional[float] = None
    delta_percentage: Optional[float] = None
    latest_date: str
    observations: List[SeriesObservation]


class FredClient:
    """Async client for fetching macroeconomic series from FRED API."""

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.fred_api_key
        self.base_url = settings.fred_base_url
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=15.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    )
    async def fetch_series_observations(
        self, series_id: str, limit: int = 12
    ) -> MacroDataPoint:
        """Fetch the latest observations for a given series ID."""
        if series_id not in FRED_SERIES:
            raise ValueError(f"Unknown series_id: {series_id}. Register it in FRED_SERIES first.")

        meta = FRED_SERIES[series_id]

        # If no API key is provided, return simulated baseline data for offline dev / testing
        if not self.api_key or self.api_key == "your_fred_api_key_here":
            logger.warning("No FRED_API_KEY provided. Using mock baseline data.")
            return self._generate_mock_datapoint(meta)

        client = self._client or httpx.AsyncClient(timeout=15.0)
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }

        url = f"{self.base_url}/series/observations"
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        raw_observations = data.get("observations", [])
        parsed_observations: List[SeriesObservation] = []

        for obs in raw_observations:
            val_str = obs.get("value", ".")
            if val_str not in (".", "", None):
                try:
                    parsed_observations.append(
                        SeriesObservation(date=obs["date"], value=float(val_str))
                    )
                except ValueError:
                    continue

        if not parsed_observations:
            raise RuntimeError(f"No valid numeric data returned by FRED for series {series_id}")

        latest = parsed_observations[0]
        prev = parsed_observations[1] if len(parsed_observations) > 1 else None

        delta = (latest.value - prev.value) if prev else None
        delta_pct = ((delta / prev.value) * 100.0) if prev and prev.value != 0 else None

        return MacroDataPoint(
            meta=meta,
            latest_value=latest.value,
            previous_value=prev.value if prev else None,
            delta=delta,
            delta_percentage=delta_pct,
            latest_date=latest.date,
            observations=parsed_observations,
        )

    async def fetch_all_registered_series(self) -> List[MacroDataPoint]:
        """Fetch current readings for all registered macroeconomic indicators."""
        results: List[MacroDataPoint] = []
        for series_id in FRED_SERIES.keys():
            try:
                dp = await self.fetch_series_observations(series_id)
                results.append(dp)
            except Exception as e:
                logger.error(f"Failed to fetch series {series_id}: {e}")
        return results

    def _generate_mock_datapoint(self, meta: MacroSeriesMeta) -> MacroDataPoint:
        """Deterministic fallback mock data for testing without active FRED credentials."""
        mock_values = {
            "FEDFUNDS": 5.33,
            "T10Y2Y": 0.15,
            "DGS10": 4.12,
            "CPIAUCSL": 314.5,
            "CPILFESL": 318.2,
            "UNRATE": 4.1,
            "PAYEMS": 158500.0,
            "M2SL": 21050.0,
        }
        val = mock_values.get(meta.series_id, 100.0)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return MacroDataPoint(
            meta=meta,
            latest_value=val,
            previous_value=val * 0.99,
            delta=val * 0.01,
            delta_percentage=1.0,
            latest_date=today,
            observations=[
                SeriesObservation(date=today, value=val),
                SeriesObservation(date="2024-01-01", value=val * 0.99),
            ],
        )
