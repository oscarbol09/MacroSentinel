"""Registry of macroeconomic series and central bank endpoints."""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class MacroSeriesMeta:
    """Metadata definition for a macroeconomic time series."""
    series_id: str
    name: str
    category: str
    unit: str
    frequency: str
    description: str


@dataclass(frozen=True)
class CentralBankSource:
    """Metadata definition for central bank communication feeds."""
    code: str
    institution: str
    feed_url: str
    feed_type: str  # 'rss', 'api', or 'html'


# Curated high-impact FRED series for macroeconomic cycle detection
FRED_SERIES: Dict[str, MacroSeriesMeta] = {
    # Yield Curves & Interest Rates
    "FEDFUNDS": MacroSeriesMeta(
        series_id="FEDFUNDS",
        name="Federal Funds Effective Rate",
        category="Monetary Policy",
        unit="Percent",
        frequency="Monthly",
        description="Benchmark overnight interest rate set by the FOMC.",
    ),
    "T10Y2Y": MacroSeriesMeta(
        series_id="T10Y2Y",
        name="10-Year Minus 2-Year Treasury Yield Spread",
        category="Yield Curve",
        unit="Percent",
        frequency="Daily",
        description="Leading recession indicator; inversion (<0) historically precedes recessions.",
    ),
    "DGS10": MacroSeriesMeta(
        series_id="DGS10",
        name="10-Year Treasury Constant Maturity Rate",
        category="Interest Rates",
        unit="Percent",
        frequency="Daily",
        description="Global benchmark risk-free rate.",
    ),
    # Inflation & Consumer Price Dynamics
    "CPIAUCSL": MacroSeriesMeta(
        series_id="CPIAUCSL",
        name="Consumer Price Index for All Urban Consumers (CPI)",
        category="Inflation",
        unit="Index 1982-1984=100",
        frequency="Monthly",
        description="Primary headline inflation gauge.",
    ),
    "CPILFESL": MacroSeriesMeta(
        series_id="CPILFESL",
        name="Core CPI (Excluding Food & Energy)",
        category="Inflation",
        unit="Index 1982-1984=100",
        frequency="Monthly",
        description="Core inflation measure monitored for sticky price pressures.",
    ),
    # Labor Market & Activity
    "UNRATE": MacroSeriesMeta(
        series_id="UNRATE",
        name="Civilian Unemployment Rate",
        category="Labor Market",
        unit="Percent",
        frequency="Monthly",
        description="Key mandate indicator for maximum sustainable employment.",
    ),
    "PAYEMS": MacroSeriesMeta(
        series_id="PAYEMS",
        name="All Employees, Total Nonfarm (Nonfarm Payrolls)",
        category="Labor Market",
        unit="Thousands of Persons",
        frequency="Monthly",
        description="Monthly job creation metric.",
    ),
    # Liquidity & Money Supply
    "M2SL": MacroSeriesMeta(
        series_id="M2SL",
        name="M2 Real Money Supply",
        category="Liquidity",
        unit="Billions of Dollars",
        frequency="Monthly",
        description="Broad measure of money supply and banking liquidity.",
    ),
}

# Central Bank Feeds
CENTRAL_BANK_SOURCES: List[CentralBankSource] = [
    CentralBankSource(
        code="FED_FOMC",
        institution="Federal Reserve (FOMC)",
        feed_url="https://www.federalreserve.gov/feeds/press_monetary.xml",
        feed_type="rss",
    ),
    CentralBankSource(
        code="ECB_MONETARY",
        institution="European Central Bank (ECB)",
        feed_url="https://www.ecb.europa.eu/rss/press.html",
        feed_type="rss",
    ),
]
