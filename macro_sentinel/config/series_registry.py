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


@dataclass(frozen=True)
class TreasuryEndpoint:
    """Metadata for a U.S. Treasury Fiscal Data API endpoint."""
    code: str
    name: str
    endpoint_path: str
    category: str
    description: str


@dataclass(frozen=True)
class BLSSeriesMeta:
    """Metadata for a Bureau of Labor Statistics time series."""
    series_id: str
    name: str
    category: str
    unit: str
    description: str


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
    "PCEPI": MacroSeriesMeta(
        series_id="PCEPI",
        name="Personal Consumption Expenditures Price Index (PCE)",
        category="Inflation",
        unit="Index 2017=100",
        frequency="Monthly",
        description="The Fed's preferred inflation measure for policy decisions.",
    ),
    "T10YIE": MacroSeriesMeta(
        series_id="T10YIE",
        name="10-Year Breakeven Inflation Rate",
        category="Inflation Expectations",
        unit="Percent",
        frequency="Daily",
        description="Market-implied inflation expectations derived from TIPS spread.",
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
    "SAHMREALTIME": MacroSeriesMeta(
        series_id="SAHMREALTIME",
        name="Sahm Rule Real-Time Recession Indicator",
        category="Recession Signals",
        unit="Percent",
        frequency="Monthly",
        description="Triggers when 3-month moving average of unemployment rises 0.50pp above its 12-month low.",
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
    "WALCL": MacroSeriesMeta(
        series_id="WALCL",
        name="Federal Reserve Total Assets",
        category="Liquidity",
        unit="Millions of Dollars",
        frequency="Weekly",
        description="Fed balance sheet size; proxy for quantitative tightening/easing pace.",
    ),
    # FX & Credit
    "DTWEXBGS": MacroSeriesMeta(
        series_id="DTWEXBGS",
        name="Trade Weighted U.S. Dollar Index (Broad Goods & Services)",
        category="FX",
        unit="Index Jan 2006=100",
        frequency="Daily",
        description="Broad dollar strength gauge affecting EM capital flows and commodity pricing.",
    ),
    "BAMLH0A0HYM2": MacroSeriesMeta(
        series_id="BAMLH0A0HYM2",
        name="ICE BofA US High Yield Option-Adjusted Spread",
        category="Credit",
        unit="Percent",
        frequency="Daily",
        description="High-yield credit spread over Treasuries; widens during stress, compresses in risk-on.",
    ),
}

# U.S. Treasury Fiscal Data API endpoints
TREASURY_ENDPOINTS: List[TreasuryEndpoint] = [
    TreasuryEndpoint(
        code="AVG_RATES",
        name="Average Interest Rates on U.S. Treasury Securities",
        endpoint_path="/v2/accounting/od/avg_interest_rates",
        category="Interest Rates",
        description="Monthly average interest rates by security type.",
    ),
    TreasuryEndpoint(
        code="DEBT_PENNY",
        name="Federal Debt to the Penny",
        endpoint_path="/v2/accounting/od/debt_to_penny",
        category="Fiscal",
        description="Daily total public debt outstanding.",
    ),
]

# BLS series for sub-component inflation and employment granularity
BLS_SERIES: Dict[str, BLSSeriesMeta] = {
    "CUSR0000SA0": BLSSeriesMeta(
        series_id="CUSR0000SA0",
        name="CPI-U All Items (SA)",
        category="Inflation",
        unit="Index 1982-1984=100",
        description="Seasonally adjusted CPI for all urban consumers.",
    ),
    "CUSR0000SA0L1E": BLSSeriesMeta(
        series_id="CUSR0000SA0L1E",
        name="CPI-U All Items Less Food & Energy (Core, SA)",
        category="Inflation",
        unit="Index 1982-1984=100",
        description="Core CPI excluding volatile food and energy components.",
    ),
    "CES0000000001": BLSSeriesMeta(
        series_id="CES0000000001",
        name="Total Nonfarm Employment (CES)",
        category="Employment",
        unit="Thousands",
        description="Establishment survey total nonfarm payroll employment.",
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
