"""
Website fetching and content extraction.
"""
import asyncio
import html as html_lib
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
    '/happyhourpromo',
    '/hh',
    '/specials',
    '/menus',
    '/menu',
    '/drinks',
    '/bar',
]
GENERIC_PRIORITY_PATHS = {'/menus', '/menu', '/drinks', '/bar'}

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

# Keywords used when crawling a homepage for happy-hour / specials links.
_HH_LINK_KEYWORDS = re.compile(
    r'happy.?hour|specials?|drink.?deal|drink.?special|weekly.?special|'
    r'daily.?special|hh\b|happy_hour',
    re.IGNORECASE,
)
_HH_HREF_KEYWORDS = re.compile(
    r'happy.?hour|happyhour|specials?|/hh\b|/hh/',
    re.IGNORECASE,
)
_HH_PAGE_RE = re.compile(r'happy.?hour|happyhour|specials?|/hh\b|/hh/', re.IGNORECASE)
_IMAGE_CONTEXT_RE = re.compile(
    r'happy.?hour|happyhour|specials?|menu|drinks?|cocktails?|beer|wine|food|hh\b',
    re.IGNORECASE,
)
_IMAGE_EXT_RE = re.compile(r'\.(?:png|jpe?g|webp|gif|avif)(?:[?#]|$)', re.IGNORECASE)
_IMAGE_SKIP_RE = re.compile(
    r'logo|icon|favicon|avatar|spinner|placeholder|transparent|tracking|pixel',
    re.IGNORECASE,
)
# Match clickable tags that can carry a link target.
_CLICKABLE_TAG_RE = re.compile(
    r'<a\b[^>]*>.*?</a>|<(?:button|div|span)\b[^>]*(?:data-href|data-url)\s*='
    r'["\'][^"\']+["\'][^>]*>.*?</(?:button|div|span)>',
    re.IGNORECASE | re.DOTALL,
)
_URL_ATTR_RE = re.compile(
    r'(?:href|data-href|data-url)\s*=\s*["\']([^"\'#?][^"\']*)["\']',
    re.IGNORECASE,
)


def _strip_query_fragment(url: str) -> str:
    """Return a URL suitable for path probing."""
    parsed = urlparse(url)
    return parsed._replace(query='', fragment='').geturl().rstrip('/')


def _path_candidate(base_url: str, path: str) -> str:
    """Append a probe path without accidentally appending after query params."""
    return f"{_strip_query_fragment(base_url)}{path}"


def homepage_fallback_urls(base_url: str) -> list[str]:
    """Return homepage-style URLs for retrying short or image-only pages."""
    if not base_url:
        return []
    base = _strip_query_fragment(base_url)
    return [f"{base}/home", f"{base}/"]


def _same_site(candidate_netloc: str, base_netloc: str) -> bool:
    """Treat bare and www hosts as the same restaurant site."""
    return candidate_netloc.lower().removeprefix('www.') == base_netloc.lower().removeprefix('www.')


def _looks_like_image_cdn(candidate_netloc: str, base_netloc: str) -> bool:
    """Allow common restaurant site-builder CDNs to host menu images."""
    host = candidate_netloc.lower().removeprefix('www.')
    base = base_netloc.lower().removeprefix('www.')
    return (
        host == base
        or host.endswith('.squarespace-cdn.com')
        or host.endswith('.wixstatic.com')
        or host.endswith('.webflow.com')
        or host.endswith('.cloudinary.com')
        or host.endswith('.imgix.net')
    )


def _dedupe_urls(urls: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        results.append(url)
        if len(results) >= limit:
            break
    return results


def extract_happy_hour_links(html: str, base_url: str) -> list[str]:
    """Return same-origin links that look like happy-hour/specials pages.

    Scans raw HTML for ``<a href=...>`` tags whose ``href`` path or visible
    anchor text contains happy-hour / specials keywords.  Returns up to 5
    absolute URLs, deduplicated and same-origin only.
    """
    if not html:
        return []

    parsed_base = urlparse(base_url)
    seen: set[str] = set()
    results: list[str] = []

    # Walk clickable tags in order so we respect document ordering.
    for m in _CLICKABLE_TAG_RE.finditer(html):
        full_tag = m.group(0)
        inner_text = re.sub(r'<[^>]+>', ' ', full_tag).strip()

        href_m = _URL_ATTR_RE.search(full_tag)
        if not href_m:
            continue
        href = href_m.group(1).strip()

        # Build absolute URL — keep only same-origin links.
        abs_url = urljoin(base_url, href)
        abs_parsed = urlparse(abs_url)
        if not _same_site(abs_parsed.netloc, parsed_base.netloc):
            continue
        # Strip query / fragment so we don't create duplicate entries.
        abs_url = f"{abs_parsed.scheme}://{abs_parsed.netloc}{abs_parsed.path}".rstrip('/')

        if abs_url in seen:
            continue

        if _HH_HREF_KEYWORDS.search(abs_parsed.path) or _HH_LINK_KEYWORDS.search(inner_text):
            seen.add(abs_url)
            results.append(abs_url)
            if len(results) >= 5:
                break

    return results


def extract_menu_images(html: str, base_url: str, max_images: int = 3) -> list[str]:
    """Return candidate menu / happy-hour image URLs from common HTML patterns."""
    if not html:
        return []

    parsed_base = urlparse(base_url)
    page_is_targeted = bool(_HH_PAGE_RE.search(urlparse(base_url).path))
    candidates: list[str] = []

    def add_url(raw_url: str, context: str) -> None:
        raw_url = html_lib.unescape(raw_url or "").strip()
        if not raw_url or raw_url.startswith("data:"):
            return
        # srcset entries look like "image.jpg 1200w"; keep only the URL part.
        raw_url = raw_url.split()[0].strip()
        if not _IMAGE_EXT_RE.search(raw_url) or _IMAGE_SKIP_RE.search(raw_url):
            return
        abs_url = urljoin(base_url, raw_url)
        parsed = urlparse(abs_url)
        if parsed.netloc and not _looks_like_image_cdn(parsed.netloc, parsed_base.netloc):
            # CDN-hosted images are common, but unrelated third-party images are not.
            if not _IMAGE_CONTEXT_RE.search(abs_url) and not _IMAGE_CONTEXT_RE.search(context):
                return
        context_blob = f"{context} {abs_url}"
        if not page_is_targeted and not _IMAGE_CONTEXT_RE.search(context_blob):
            return
        candidates.append(abs_url)

    tag_re = re.compile(r'<(?:img|source|meta)\b[^>]*>', re.IGNORECASE | re.DOTALL)
    attr_re = re.compile(
        r'(?:src|data-src|data-lazy-src|data-original|content)\s*=\s*["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    srcset_re = re.compile(r'(?:srcset|data-srcset)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    bg_re = re.compile(r'url\(["\']?([^)"\']+)["\']?\)', re.IGNORECASE)

    for m in tag_re.finditer(html):
        tag = m.group(0)
        tag_start = max(0, m.start() - 160)
        tag_end = min(len(html), m.end() + 160)
        context = re.sub(r'<[^>]+>', ' ', html[tag_start:tag_end])
        for attr in attr_re.finditer(tag):
            add_url(attr.group(1), context)
        for attr in srcset_re.finditer(tag):
            for part in attr.group(1).split(','):
                add_url(part.strip(), context)

    for m in bg_re.finditer(html):
        start = max(0, m.start() - 160)
        end = min(len(html), m.end() + 160)
        context = re.sub(r'<[^>]+>', ' ', html[start:end])
        add_url(m.group(1), context)

    return _dedupe_urls(candidates, max_images)


class WebsiteFetcher:
    """Fetch and clean website content."""

    def __init__(self, delay: float = 1.0, cache_dir: Optional[Path] = None):
        self.delay = delay
        self.cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def find_menu_page(self, base_url: str) -> Optional[str]:
        """Find happy hour or menu page by checking priority paths.

        First checks all PRIORITY_PATHS via HEAD requests.  If none return
        HTTP 200, fetches the homepage and crawls it for same-origin links
        whose href or anchor text contains happy-hour / specials keywords.
        """
        if not base_url:
            return None

        # Ensure URL ends without slash for joining, and discard tracking
        # params so probe paths are appended to the path, not the query string.
        base_url = _strip_query_fragment(base_url)

        explicit_paths = [p for p in PRIORITY_PATHS if p not in GENERIC_PRIORITY_PATHS]
        generic_paths = [p for p in PRIORITY_PATHS if p in GENERIC_PRIORITY_PATHS]

        # 1. Try explicit happy-hour / specials paths first.
        for path in explicit_paths:
            url = _path_candidate(base_url, path)
            try:
                response = requests.head(url, headers=HEADERS, timeout=10,
                                        allow_redirects=True)
                if response.status_code == 200:
                    return url
            except requests.RequestException:
                pass
            time.sleep(0.5)

        # 2. Crawl homepage for happy-hour / specials links.
        try:
            homepage_html = requests.get(
                base_url, headers=HEADERS, timeout=30, allow_redirects=True
            ).text
            crawled = extract_happy_hour_links(homepage_html, base_url)
            for url in crawled:
                try:
                    r = requests.head(url, headers=HEADERS, timeout=10,
                                      allow_redirects=True)
                    if r.status_code == 200:
                        return url
                except requests.RequestException:
                    pass
                time.sleep(0.3)
        except requests.RequestException:
            pass

        # 3. Fall back to broad menu/drinks pages only after site-authored
        # happy-hour / specials links have had a chance to win.
        for path in generic_paths:
            url = _path_candidate(base_url, path)
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
            """Find the best happy-hour/menu URL for a restaurant website.

            Strategy:
            1. Concurrently HEAD-check explicit happy-hour/specials paths and
               fetch the homepage HTML (to enable link-crawling).
            2. Return the first explicit priority path that responds with HTTP
               200, preserving the original ordering.
            3. If no explicit priority path matched, scan the homepage HTML for
               same-origin links whose href or anchor text contains
               happy-hour / specials keywords, HEAD-check those concurrently,
               and return the first live one.
            4. Try broad menu/drinks pages, then fall back to the base URL.
            """
            if not base_url:
                return None
            base_url = _strip_query_fragment(base_url)

            async def check(url: str) -> Optional[str]:
                try:
                    r = await self.client.head(url, timeout=10)
                    if r.status_code == 200:
                        return url
                except Exception:
                    pass
                return None

            explicit_paths = [p for p in PRIORITY_PATHS if p not in GENERIC_PRIORITY_PATHS]
            generic_paths = [p for p in PRIORITY_PATHS if p in GENERIC_PRIORITY_PATHS]

            # Launch explicit priority-path checks AND homepage fetch in parallel.
            priority_urls = [_path_candidate(base_url, p) for p in explicit_paths]
            homepage_task = asyncio.ensure_future(self.afetch(base_url, use_cache=True))
            check_tasks = [asyncio.ensure_future(check(u)) for u in priority_urls]

            priority_results, homepage_html = await asyncio.gather(
                asyncio.gather(*check_tasks),
                homepage_task,
            )

            # 1. Return first explicit priority match.
            for result in priority_results:
                if result:
                    return result

            # 2. Crawl homepage for happy-hour/specials links.
            if homepage_html:
                crawled = extract_happy_hour_links(homepage_html, base_url)
                if crawled:
                    crawl_checks = await asyncio.gather(*[check(u) for u in crawled])
                    for result in crawl_checks:
                        if result:
                            return result

            # 3. Broad menu/drinks pages are useful, but should not beat a
            # restaurant-authored happy-hour/specials link.
            generic_results = await asyncio.gather(
                *[check(_path_candidate(base_url, p)) for p in generic_paths]
            )
            for result in generic_results:
                if result:
                    return result

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

            Fetches raw HTML (no JS render) and scans common image patterns:
            ``img``/``source`` attributes, Open Graph image tags, srcsets, and
            CSS background URLs. Returns at most 3 candidates so vision calls
            stay cheap.
            """
            html = await self.afetch(url, use_cache=True)
            if not html:
                return []
            return extract_menu_images(html, url)

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
