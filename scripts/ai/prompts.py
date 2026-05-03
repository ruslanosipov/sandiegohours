"""
All AI prompt templates in one place.
"""
from typing import Optional

HAPPY_HOUR_PARSER_PROMPT = """Parse this website content and extract happy hour schedule information.

Website content:
{text}

CRITICAL: Only extract HAPPY HOUR times, NOT regular opening hours.
- Happy hours are special discount periods (e.g., "3-6 PM", "4-7 PM")
- Opening hours are when the restaurant is open (e.g., "11 AM - 10 PM")
- If you only see "Opening Hours", "Hours", "Business Hours" - these are NOT happy hours
- Look for explicit mentions of "happy hour", "hh", "drink specials", "appetizer specials"

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

Confidence can be "high", "medium", or "low".
- Use "high" only if you see explicit "happy hour" text
- Use "medium" if you see "specials" or "discounts" with times
- Use "low" if you're unsure
- Use "Closed" for days with no happy hour

If no happy hour info found, return empty happy_hours array and confidence "none"."""

MENU_PARSER_PROMPT = """Parse this happy hour menu from {restaurant_name}.
{schedule_block}Menu content:
{text}

SCOPE (most important):
- Consider ONLY drink and food items that are clearly **happy hour / HH / happy-hour specials** pricing (same subsection, same labeled lines, or wording like "during happy hour", "HH price", "happy hour menu").
- Do NOT pick the cheapest item on the whole page if it comes from: wine-by-the-glass or bottle lists, brunch/lunch/dinner menus, regular bar or dining menus, catering, or retail — unless that exact line is explicitly tied to happy hour / HH / specials-for-happy-hour.
- If you cannot find any drink or food line that is clearly happy-hour-priced in the text, return null for that field (do NOT fall back to the cheapest wine or plate elsewhere on the page).

CRITICAL RULES:
1. ONLY extract items that are EXPLICITLY listed in the text above
2. DO NOT make up items, DO NOT use "typical" happy hour items
3. If the text is empty, too short, or doesn't mention specific happy-hour-priced items, return null
4. The text might be a loading page or error page - if so, return null

Extract drink and food items with prices ONLY if explicitly shown under the scope above. Look for:
- Dollar amounts with items in happy hour context (e.g., "$6 HH beer", "$8 sliders during happy hour")
- Sections titled Happy Hour, HH, or equivalent with listed prices

Return JSON in this exact format:
{{
  "drink": {{"name": "cheapest happy-hour drink with price", "price": 5.00}},
  "food": {{"name": "cheapest happy-hour food with price", "price": 6.00}},
  "short_summary": "$1 wings, $3 sliders, $5 bottled, $7 draft and cocktails"
}}

Examples of VALID responses (only if text contains these as happy-hour-priced lines):
{{"drink": {{"name": "$5 bottled beer", "price": 5}}, "food": {{"name": "$1 wings", "price": 1}}, "short_summary": "$1 wings, $3 sliders, $5 bottled and $7 cocktails"}}

If text is empty, too short (< 100 chars), or doesn't contain identifiable happy hour-priced items:
{{"drink": null, "food": null, "short_summary": ""}}

Rules:
- ONLY use items EXPLICITLY in the text AND within the SCOPE above
- Find the CHEAPEST qualifying happy-hour drink and CHEAPEST qualifying happy-hour food (if any)
- Include 3-5 popular happy-hour items in short_summary (ONLY if found)
- short_summary must be UNDER 15 words
- Order by price: cheapest first
- Use "and" before last item
- If no qualifying items found, return null/empty"""


def format_happy_hour_prompt(text: str) -> str:
    """Format the happy hour parser prompt."""
    return HAPPY_HOUR_PARSER_PROMPT.format(text=text)


def format_menu_prompt(
    restaurant_name: str,
    text: str,
    happy_hour_times: Optional[str] = None,
) -> str:
    """Format the menu parser prompt."""
    schedule_block = ""
    if happy_hour_times and str(happy_hour_times).strip():
        schedule_block = (
            "Known happy hour schedule (for context only; happy-hour *pricing* must still appear in the menu text): "
            f"{str(happy_hour_times).strip()}\n\n"
        )
    return MENU_PARSER_PROMPT.format(
        restaurant_name=restaurant_name,
        text=text,
        schedule_block=schedule_block,
    )
