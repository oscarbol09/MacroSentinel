"""Storage module for MacroSentinel persistence and deduplication."""

from .sqlite_cache import SQLiteCache

__all__ = ["SQLiteCache"]
