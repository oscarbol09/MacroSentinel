"""Dispatchers package for alerting and visual rendering."""

from .console import ConsoleDispatcher
from .telegram import TelegramDispatcher

__all__ = ["ConsoleDispatcher", "TelegramDispatcher"]
