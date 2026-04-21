"""
All AI prompt templates in one place.
"""

HAPPY_HOUR_PARSER_PROMPT = """Parse this website content and extract happy hour schedule information.

Website content:
{text}

Extract happy hour times for each day of the week. Look for:
- Days of week (Monday, Tuesday, etc.)
- Time ranges (3-6 PM, 4:00-7:00 PM, etc.)
- "Closed" or similar indicators

Return JSON in this exact format:
{{
  "happy_hours": [
    {{"day": "Monday", "times": "3:00 PM - 6:00 PM"}},
    {{"day": "Tuesday", "times": "3:00 PM - 6:00 PM"}},
    {{"day": "Wednesday", "times": "3:00 PM - 6:00 PM"}},
    {{"day": "Thursday", "times": "3:00 PM - 6:00 PM"}},
    {{"day": "Friday", "times": "4:00 PM - 7:00 PM"}},
    {{"day": "Saturday", "times": "Closed"}},
    {{"day": "Sunday", "times": "Closed"}}
  ],
  "confidence": "high"
}}

Confidence can be "high", "medium", or "low". Use "Closed" for days with no happy hour.
If no happy hour info found, return empty happy_hours array."""

MENU_PARSER_PROMPT = """Parse this happy hour menu from {restaurant_name}.

Menu content:
{text}

Extract ALL drink and food items with prices you can find. Look for patterns like:
- $5 bottled beer, $7 draft, $8 cocktails
- $1 wings, $3 sliders, $8 nachos

Return JSON in this exact format:
{{
  "drink": {{"name": "cheapest drink with price", "price": 5.00}},
  "food": {{"name": "cheapest food with price", "price": 6.00}},
  "short_summary": "$1 wings, $3 sliders, $5 bottled, $7 draft and cocktails"
}}

Examples:
{{"drink": {{"name": "$5 bottled beer", "price": 5}}, "food": {{"name": "$1 wings", "price": 1}}, "short_summary": "$1 wings, $3 sliders, $5 bottled and $7 cocktails"}}
{{"drink": {{"name": "$7 draft pours", "price": 7}}, "food": {{"name": "$3 chicken sliders", "price": 3}}, "short_summary": "$3 sliders, $7 draft and $9 cocktails"}}

Rules:
- Find the CHEAPEST drink and CHEAPEST food item
- Include 3-5 popular items in short_summary
- short_summary must be UNDER 15 words
- Order by price: cheapest first
- Use "and" before last item

If no happy hour prices found, return null for drink and food, and empty string for short_summary."""


def format_happy_hour_prompt(text: str) -> str:
    """Format the happy hour parser prompt."""
    return HAPPY_HOUR_PARSER_PROMPT.format(text=text)


def format_menu_prompt(restaurant_name: str, text: str) -> str:
    """Format the menu parser prompt."""
    return MENU_PARSER_PROMPT.format(restaurant_name=restaurant_name, text=text)
