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

try:
    from playwright.async_api import async_playwright
    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False

# Priority paths to check for happy hour info
PRIORITY_PATHS = [
    '/menus/happy-hour',
    '/menu/happy-hour',
    '/happy-hour',
    '/happyhour',
    '/hh',
    '/specials',
    '/menus',
    '/menu',
    '/drinks',
    '/bar',
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Generators of JS-heavy single-page sites whose useful content lives outside
# the static HTML. When detected we fall back to a real browser render.
SPA_GENERATOR_MARKERS = (
    'wix.com website builder',
    'squarespace',
    'webflow',
    'shopify',
    'duda',
    'weebly',
)

# Below this many *cleaned* characters, the static HTML almost certainly
# rendered to a JS shell and we should retry with a browser.
JS_RENDER_MIN_CLEANED_CHARS = 300


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
            enable_js_render: bool = True,
            max_concurrent_renders: int = 2,
        ):
            self.delay = delay
            self.cache_dir = cache_dir
            if cache_dir:
                cache_dir.mkdir(parents=True, exist_ok=True)
            self._client = client
            self._owned_client = client is None
            self._cache_lock = asyncio.Lock()
            self._fetch_semaphore = asyncio.Semaphore(max_concurrent_fetches)
            # JS render state (lazy: browser only spun up if needed)
            self._js_enabled = enable_js_render and _HAS_PLAYWRIGHT
            self._render_semaphore = asyncio.Semaphore(max_concurrent_renders)
            self._playwright = None
            self._browser = None
            self._browser_lock = asyncio.Lock()

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

        @staticmethod
        def _looks_like_spa(html: str) -> bool:
            """Detect known JS-heavy site builders in raw HTML."""
            if not html:
                return False
            head = html[:5000].lower()
            return any(marker in head for marker in SPA_GENERATOR_MARKERS)

        async def _ensure_browser(self):
            """Lazily start Playwright + browser on first use."""
            if self._browser is not None:
                return
            async with self._browser_lock:
                if self._browser is not None:
                    return
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)

        async def _render_js(self, url: str) -> Optional[str]:
            """Render `url` in a real browser and return visible text (already cleaned).

            Collects text from the main document AND every child frame (Wix and
            similar SPAs frequently host menu sections inside HTML iframes).
            """
            if not self._js_enabled:
                return None
            try:
                await self._ensure_browser()
            except Exception as e:
                print(f"  Playwright unavailable for {url}: {e}")
                self._js_enabled = False
                return None

            async with self._render_semaphore:
                context = None
                try:
                    context = await self._browser.new_context(
                        user_agent=HEADERS['User-Agent'],
                        viewport={"width": 1280, "height": 900},
                    )
                    page = await context.new_page()
                    try:
                        await page.goto(url, wait_until='networkidle', timeout=30000)
                    except Exception:
                        try:
                            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        except Exception as e:
                            print(f"  JS render navigation failed for {url}: {e}")
                            return None

                    # Trigger lazy-load by scrolling the page top-to-bottom.
                    try:
                        await page.evaluate(
                            "() => new Promise(r => { let y=0; const id=setInterval(()=>{ "
                            "window.scrollTo(0,y); y+=600; "
                            "if(y>document.body.scrollHeight){clearInterval(id);r();}},120);})"
                        )
                        await page.wait_for_timeout(1500)
                    except Exception:
                        pass

                    # Pull text from the main frame and every child frame.
                    parts: list[str] = []
                    for frame in page.frames:
                        try:
                            t = await frame.evaluate(
                                '() => document.body ? document.body.innerText : ""'
                            )
                        except Exception:
                            t = ""
                        if t and t.strip():
                            parts.append(t)
                    text = "\n".join(parts)
                    if not text:
                        return None
                    text = re.sub(r'\s+', ' ', text).strip()
                    return text[:8000]
                finally:
                    if context is not None:
                        try:
                            await context.close()
                        except Exception:
                            pass

        async def _read_render_cache(self, url: str) -> Optional[str]:
            if not self.cache_dir:
                return None
            async with self._cache_lock:
                p = self.cache_dir / f"{self._cache_key(url)}.rendered.txt"
                if p.exists():
                    try:
                        return p.read_text(encoding='utf-8')
                    except OSError:
                        return None
            return None

        async def _write_render_cache(self, url: str, text: str) -> None:
            if not self.cache_dir or not text:
                return
            async with self._cache_lock:
                p = self.cache_dir / f"{self._cache_key(url)}.rendered.txt"
                try:
                    p.write_text(text, encoding='utf-8')
                except OSError:
                    pass

        async def afetch_clean(self, url: str) -> Optional[str]:
            """Fetch + clean, falling back to a real browser for JS-rendered sites."""
            cached_render = await self._read_render_cache(url)
            if cached_render:
                return cached_render

            html = await self.afetch(url)
            cleaned = self.clean_html(html) if html else ""

            needs_render = self._js_enabled and (
                not cleaned
                or len(cleaned) < JS_RENDER_MIN_CLEANED_CHARS
                or (html and self._looks_like_spa(html))
            )
            if needs_render:
                try:
                    short_name = url[:80]
                    print(f"  JS render fallback: {short_name}")
                except UnicodeEncodeError:
                    print("  JS render fallback: <unicode url>")
                rendered = await self._render_js(url)
                if rendered and len(rendered) > len(cleaned):
                    await self._write_render_cache(url, rendered)
                    return rendered

            return cleaned or None

        async def afetch_menu_images(self, url: str) -> list:
            """Return a list of image URLs that look like menu/happy-hour images.

            Fetches the raw HTML (no JS render) and scans for <img> tags whose
            ``src`` or ``alt`` attribute suggests a menu or happy-hour image.
            Returns at most 3 candidate URLs so vision calls stay cheap.
            """
            html = await self.afetch(url, use_cache=True)
            if not html:
                return []

            _MENU_IMG_RE = re.compile(
                r'<img[^>]+(?:src|data-src)\s*=\s*["\']([^"\']+)["\'][^>]*>',
                re.IGNORECASE,
            )
            _HH_ALT_RE = re.compile(
                r'(?:happy.?hour|menu|specials?|hh)',
                re.IGNORECASE,
            )
            _IMG_EXT_RE = re.compile(r'\.(png|jpe?g|webp|gif|avif)', re.IGNORECASE)

            candidates = []
            seen = set()
            for m in _MENU_IMG_RE.finditer(html):
                src = m.group(1).strip()
                # Grab the surrounding tag to check the alt attribute
                tag_start = max(0, m.start() - 20)
                tag = html[tag_start: m.end() + 20]
                alt_match = re.search(r'alt\s*=\s*["\']([^"\']*)["\']', tag, re.IGNORECASE)
                alt = alt_match.group(1) if alt_match else ''

                if not _IMG_EXT_RE.search(src):
                    continue
                if src in seen:
                    continue
                seen.add(src)

                if _HH_ALT_RE.search(alt) or _HH_ALT_RE.search(src):
                    # Make absolute URL
                    if not src.startswith(('http://', 'https://')):
                        src = urljoin(url, src)
                    candidates.append(src)
                    if len(candidates) >= 3:
                        break

            return candidates

        def _cache_key(self, url: str) -> str:
            import hashlib
            return hashlib.md5(url.encode()).hexdigest()[:16]

        async def close(self):
            if self._browser is not None:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._playwright is not None:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
            if self._owned_client and self._client is not None:
                await self._client.aclose()
                self._client = None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            await self.close()
