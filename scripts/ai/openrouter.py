"""
Single OpenRouter client with retry logic and rate limiting.
"""
import asyncio
import time
from typing import Optional

import requests

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False


class OpenRouterClient:
    """Client for OpenRouter API with built-in retry logic."""

    DEFAULT_MODEL = "google/gemini-2.5-flash-lite"

    def __init__(self, api_key: str, model: str = None, max_retries: int = 3):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL
        self.max_retries = max_retries
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://happy-hour-finder.local",
            "X-Title": "Happy Hour Finder",
            "Content-Type": "application/json"
        }

    def complete(self, prompt: str, system: str = None, temperature: float = 0.1) -> str:
        """
        Send completion request with exponential backoff retry.

        Args:
            prompt: The user prompt
            system: Optional system message
            temperature: Sampling temperature (0-1)

        Returns:
            Response content string

        Raises:
            Exception: After max retries exhausted
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers=self.headers,
                    json={
                        'model': self.model,
                        'messages': messages,
                        'temperature': temperature,
                    },
                    timeout=60
                )

                if response.status_code == 429:
                    wait = 2 ** (attempt + 1)
                    print(f"  Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content']

            except requests.exceptions.RequestException as e:
                err_msg = str(e) or type(e).__name__
                if attempt == self.max_retries - 1:
                    raise Exception(f"OpenRouter API failed after {self.max_retries} retries: {err_msg}")
                wait = 2 ** (attempt + 1)
                print(f"  Request failed: {err_msg}, retrying in {wait}s...")
                time.sleep(wait)

        raise Exception("Max retries exhausted")


if _HAS_HTTPX:
    class AsyncOpenRouterClient:
        """Async OpenRouter client with concurrency control."""

        DEFAULT_MODEL = "google/gemini-2.5-flash-lite"

        def __init__(
            self,
            api_key: str,
            model: str = None,
            max_retries: int = 3,
            max_concurrent: int = 50,
            client: Optional["httpx.AsyncClient"] = None,
        ):
            self.api_key = api_key
            self.model = model or self.DEFAULT_MODEL
            self.max_retries = max_retries
            self.semaphore = asyncio.Semaphore(max_concurrent)
            self.headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://happy-hour-finder.local",
                "X-Title": "Happy Hour Finder",
                "Content-Type": "application/json"
            }
            self._client = client
            self._owned_client = client is None

        @property
        def client(self) -> "httpx.AsyncClient":
            if self._client is None:
                self._client = httpx.AsyncClient(timeout=60)
            return self._client

        async def acomplete(self, prompt: str, system: str = None, temperature: float = 0.1) -> str:
            """Send async completion request with concurrency control and retry."""
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            async with self.semaphore:
                for attempt in range(self.max_retries):
                    try:
                        response = await self.client.post(
                            'https://openrouter.ai/api/v1/chat/completions',
                            headers=self.headers,
                            json={
                                'model': self.model,
                                'messages': messages,
                                'temperature': temperature,
                            },
                        )

                        if response.status_code == 429:
                            wait = 2 ** (attempt + 1)
                            print(f"  Rate limited, waiting {wait}s...")
                            await asyncio.sleep(wait)
                            continue

                        response.raise_for_status()
                        data = response.json()
                        return data['choices'][0]['message']['content']

                    except httpx.HTTPStatusError as e:
                        err_msg = str(e) or type(e).__name__
                        if e.response.status_code == 429:
                            wait = 2 ** (attempt + 1)
                            print(f"  Rate limited, waiting {wait}s...")
                            await asyncio.sleep(wait)
                            continue
                        if attempt == self.max_retries - 1:
                            raise Exception(f"OpenRouter API failed after {self.max_retries} retries: {err_msg}")
                        wait = 2 ** (attempt + 1)
                        print(f"  Request failed: {err_msg}, retrying in {wait}s...")
                        await asyncio.sleep(wait)

                    except httpx.RequestError as e:
                        err_msg = str(e) or type(e).__name__
                        if attempt == self.max_retries - 1:
                            raise Exception(f"OpenRouter API failed after {self.max_retries} retries: {err_msg}")
                        wait = 2 ** (attempt + 1)
                        print(f"  Request failed: {err_msg}, retrying in {wait}s...")
                        await asyncio.sleep(wait)

            raise Exception("Max retries exhausted")

        async def close(self):
            if self._owned_client and self._client is not None:
                await self._client.aclose()
                self._client = None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            await self.close()
