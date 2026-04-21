"""
Content parsing utilities for AI responses.
"""
import json
import re
from typing import Optional, Dict, Any


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from markdown or raw text."""
    # Try markdown code blocks first
    patterns = [
        r'```json\n?(.*?)\n?```',
        r'```\n?(.*?)\n?```',
        r'\{[\s\S]*\}'  # Raw JSON object
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                json_str = match.group(1) if match.groups() else match.group(0)
                return json.loads(json_str.strip())
            except json.JSONDecodeError:
                continue
    
    # Try parsing entire text as JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


def parse_happy_hour_response(content: str) -> Dict[str, Any]:
    """Parse AI response for happy hour data."""
    data = extract_json(content)
    if not data:
        return {'happy_hours': [], 'confidence': 'low'}
    
    return {
        'happy_hours': data.get('happy_hours', []),
        'confidence': data.get('confidence', 'low')
    }


def parse_menu_response(content: str) -> Dict[str, Any]:
    """Parse AI response for menu data."""
    data = extract_json(content)
    if not data:
        return {
            'drink': None,
            'food': None,
            'short_summary': ''
        }
    
    return {
        'drink': data.get('drink'),
        'food': data.get('food'),
        'short_summary': data.get('short_summary', '')
    }


def format_happy_hour_times(schedule: list) -> str:
    """Convert schedule list to pipe-separated string."""
    parts = []
    for item in schedule:
        day = item.get('day', '')
        times = item.get('times', '')
        if day and times:
            parts.append(f"{day}: {times}")
    return ' | '.join(parts)
