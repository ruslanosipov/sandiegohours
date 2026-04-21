"""
Single OpenRouter client with retry logic and rate limiting.
"""
import time
import requests
from typing import Optional

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
                if attempt == self.max_retries - 1:
                    raise Exception(f"OpenRouter API failed after {self.max_retries} retries: {e}")
                wait = 2 ** (attempt + 1)
                print(f"  Request failed: {e}, retrying in {wait}s...")
                time.sleep(wait)
        
        raise Exception("Max retries exhausted")
