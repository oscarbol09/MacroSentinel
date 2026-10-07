"""Configuration package for MacroSentinel."""

from .series_registry import FRED_SERIES, CentralBankSource
from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings", "FRED_SERIES", "CentralBankSource"]
