"""AI module for OpenRouter integration."""
from .openrouter import OpenRouterClient

try:
    from .openrouter import AsyncOpenRouterClient
except ImportError:
    AsyncOpenRouterClient = None  # type: ignore

from .prompts import format_happy_hour_prompt, format_menu_prompt

__all__ = [
    'OpenRouterClient',
    'AsyncOpenRouterClient',
    'format_happy_hour_prompt',
    'format_menu_prompt',
]
