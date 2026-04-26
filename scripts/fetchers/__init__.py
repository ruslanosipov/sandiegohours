"""Fetchers module for data acquisition."""
from .website import WebsiteFetcher

try:
    from .website import AsyncWebsiteFetcher
except ImportError:
    AsyncWebsiteFetcher = None  # type: ignore

__all__ = ['WebsiteFetcher', 'AsyncWebsiteFetcher']
