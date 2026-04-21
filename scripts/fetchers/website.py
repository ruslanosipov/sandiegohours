"""
Website fetching and content extraction.
"""
import re
import requests
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

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
