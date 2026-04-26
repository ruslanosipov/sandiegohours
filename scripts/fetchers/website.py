"""
Website fetching and content extraction.
"""
import asyncio
import re
import requests
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

# Priority paths to check for happy hour info
PRIORITY_PATHS = [
    '/happy-hour',
    '/happyhour',
    '/hh',
    '/specials',
    '/menu',
    '/drinks',
    '/bar',
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


class WebsiteFetcher:
    """Fetch and clean website content."""

    def __init__(self, delay: float = 1.0, cache_dir: Optional[Path] = None):
        self.delay = delay
        self.cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def find_menu_page(self, base_url: str) -> Optional[str]:
        """Find happy hour or menu page by checking priority paths."""
        if not base_url:
            return None

        # Ensure URL ends without slash for joining
        base_url = base_url.rstrip('/')

        # Try priority paths first
        for path in PRIORITY_PATHS:
            url = f"{base_url}{path}"
            try:
                response = requests.head(url, headers=HEADERS, timeout=10,
                                        allow_redirects=True)
                if response.status_code == 200:
                    return url
            except requests.RequestException:
                pass
            time.sleep(0.5)

        return base_url

    def fetch(self, url: str, use_cache: bool = True) -> Optional[str]:
        """Fetch HTML content with optional caching."""
        if not url:
            return None

        # Check cache
        if use_cache and self.cache_dir:
            cache_key = self._cache_key(url)
            cache_path = self.cache_dir / f"{cache_key}.html"
            if cache_path.exists():
                return cache_path.read_text(encoding='utf-8')

        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            html = response.text

            # Save to cache
            if use_cache and self.cache_dir:
                cache_key = self._cache_key(url)
                cache_path = self.cache_dir / f"{cache_key}.html"
                cache_path.write_text(html, encoding='utf-8')

            time.sleep(self.delay)
            return html

        except requests.RequestException as e:
            print(f"  Error fetching {url}: {e}")
            return None

    def clean_html(self, html: str) -> str:
        """Clean HTML to extract readable text."""
        # Remove scripts and styles
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)

        # Remove other tags
        html = re.sub(r'<[^>]+>', ' ', html)

        # Normalize whitespace
        html = re.sub(r'\s+', ' ', html)

        return html.strip()[:8000]  # Limit length

    def fetch_clean(self, url: str) -> Optional[str]:
        """Fetch and clean in one step."""
        html = self.fetch(url)
        if html:
            return self.clean_html(html)
        return None

    def _cache_key(self, url: str) -> str:
        """Generate cache key from URL."""
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()[:16]


def normalize_url(url: str) -> Optional[str]:
    """Normalize URL, adding http:// if needed."""
    if not url:
        return None
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    return url


if _HAS_HTTPX:
    class AsyncWebsiteFetcher:
        """Async website fetcher with concurrent priority-path checks."""

        def __init__(
            self,
            delay: float = 0.0,
            cache_dir: Optional[Path] = None,
            client: Optional["httpx.AsyncClient"] = None,
            max_concurrent_fetches: int = 5,
        ):
            self.delay = delay
            self.cache_dir = cache_dir
            if cache_dir:
                cache_dir.mkdir(parents=True, exist_ok=True)
            self._client = client
            self._owned_client = client is None
            self._cache_lock = asyncio.Lock()
            self._fetch_semaphore = asyncio.Semaphore(max_concurrent_fetches)

        @property
        def client(self) -> "httpx.AsyncClient":
            if self._client is None:
                self._client = httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True)
            return self._client

        async def afind_menu_page(self, base_url: str) -> Optional[str]:
            """Check priority paths concurrently."""
            if not base_url:
                return None
            base_url = base_url.rstrip('/')

            async def check(path: str) -> Optional[str]:
                url = f"{base_url}{path}"
                try:
                    r = await self.client.head(url, timeout=10)
                    if r.status_code == 200:
                        return url
                except Exception:
                    pass
                return None

            tasks = [check(p) for p in PRIORITY_PATHS]
            results = await asyncio.gather(*tasks)
            for r in results:
                if r:
                    return r
            return base_url

        async def afetch(self, url: str, use_cache: bool = True) -> Optional[str]:
            """Fetch HTML with async HTTP and caching."""
            if not url:
                return None

            # Serialize all cache operations to avoid Windows file-lock races
            if use_cache and self.cache_dir:
                async with self._cache_lock:
                    cache_key = self._cache_key(url)
                    cache_path = self.cache_dir / f"{cache_key}.html"
                    if cache_path.exists():
                        try:
                            return cache_path.read_text(encoding='utf-8')
                        except OSError:
                            pass  # File may be locked; fall through to fetch

            async with self._fetch_semaphore:
                try:
                    response = await self.client.get(url)
                    response.raise_for_status()
                    html = response.text

                    if use_cache and self.cache_dir:
                        async with self._cache_lock:
                            cache_key = self._cache_key(url)
                            cache_path = self.cache_dir / f"{cache_key}.html"
                            cache_path.write_text(html, encoding='utf-8')

                    if self.delay:
                        await asyncio.sleep(self.delay)
                    return html

                except httpx.HTTPError as e:
                    print(f"  Error fetching {url}: {e}")
                    return None

        def clean_html(self, html: str) -> str:
            """Clean HTML to extract readable text."""
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
            html = re.sub(r'<[^>]+>', ' ', html)
            html = re.sub(r'\s+', ' ', html)
            return html.strip()[:8000]

        async def afetch_clean(self, url: str) -> Optional[str]:
            """Fetch and clean in one async step."""
            html = await self.afetch(url)
            if html:
                return self.clean_html(html)
            return None

        def _cache_key(self, url: str) -> str:
            import hashlib
            return hashlib.md5(url.encode()).hexdigest()[:16]

        async def close(self):
            if self._owned_client and self._client is not None:
                await self._client.aclose()
                self._client = None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            await self.close()
