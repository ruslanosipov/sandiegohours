"""
Disk-backed cache for Google Places API responses.

- Text Search cache keyed by (params hash) with TTL
- Place Details cache keyed by place_id with TTL
"""
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class GoogleAPICache:
    """Cache Google API JSON responses to disk."""

    def __init__(self, cache_dir: Path, ttl_seconds: int = 2592000):
        """
        Args:
            cache_dir: Directory to store cache files
            ttl_seconds: Time-to-live in seconds (default 30 days)
        """
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self.search_dir = cache_dir / "search"
        self.details_dir = cache_dir / "details"
        self.search_dir.mkdir(parents=True, exist_ok=True)
        self.details_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Text Search cache
    # ------------------------------------------------------------------

    def _search_key(self, keyword: str, location: Optional[str], radius: int,
                    page_token: Optional[str], location_restriction: Optional[dict]) -> str:
        """Deterministic hash for a search request."""
        data = json.dumps({
            "keyword": keyword,
            "location": location,
            "radius": radius,
            "page_token": page_token,
            "location_restriction": location_restriction,
        }, sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()[:16]

    def get_search(self, keyword: str, location: Optional[str] = None,
                   radius: int = 2400, page_token: Optional[str] = None,
                   location_restriction: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """Return cached search result or None if missing/expired."""
        key = self._search_key(keyword, location, radius, page_token, location_restriction)
        path = self.search_dir / f"{key}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - data.get("_cached_at", 0) > self.ttl_seconds:
                return None
            return data.get("result")
        except (json.JSONDecodeError, OSError):
            return None

    def set_search(self, keyword: str, location: Optional[str] = None,
                   radius: int = 2400, page_token: Optional[str] = None,
                   location_restriction: Optional[dict] = None,
                   result: Dict[str, Any] = None):
        """Cache a search result."""
        key = self._search_key(keyword, location, radius, page_token, location_restriction)
        path = self.search_dir / f"{key}.json"
        payload = {"_cached_at": time.time(), "result": result}
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # Place Details cache
    # ------------------------------------------------------------------

    def get_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Return cached place details or None if missing/expired."""
        path = self.details_dir / f"{place_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - data.get("_cached_at", 0) > self.ttl_seconds:
                return None
            return data.get("result")
        except (json.JSONDecodeError, OSError):
            return None

    def set_details(self, place_id: str, result: Dict[str, Any]):
        """Cache place details."""
        path = self.details_dir / f"{place_id}.json"
        payload = {"_cached_at": time.time(), "result": result}
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # Batch helpers
    # ------------------------------------------------------------------

    def get_details_batch(self, place_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Fetch cached details for many place IDs at once."""
        return {pid: self.get_details(pid) for pid in place_ids}

    def set_details_batch(self, results: Dict[str, Dict[str, Any]]):
        """Cache many place details at once."""
        for pid, result in results.items():
            self.set_details(pid, result)

    def invalidate_all(self):
        """Clear the entire cache."""
        for d in (self.search_dir, self.details_dir):
            for f in d.glob("*.json"):
                f.unlink(missing_ok=True)
