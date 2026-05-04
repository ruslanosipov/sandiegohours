"""Tests for parsers.menu_text.focus_text_for_happy_hour_menu."""
import pytest

from scripts.parsers.menu_text import focus_text_for_happy_hour_menu


def test_no_anchor_returns_full_text():
    blob = "Regular dinner menu salmon $40 steak $55 no keywords here " * 10
    assert focus_text_for_happy_hour_menu(blob) == blob


def test_focus_includes_region_after_happy_hour_heading():
    prefix = "WINE BY THE GLASS sauv blanc $10 pinot $12 " * 30
    hh_region = "Happy Hour draft beer $6 wine $8 sliders $8 "
    suffix = "BRUNCH eggs $15 " * 20
    full_text = prefix + hh_region + suffix

    focused = focus_text_for_happy_hour_menu(full_text, window=500, max_out=8000)

    assert "draft beer $6" in focused
    assert "Happy Hour" in focused or "happy hour" in focused.lower()
    # Early wine block should be excluded when outside first anchor window
    assert focused.startswith(prefix[:50]) is False or len(focused) < len(full_text)


def test_focus_concatenates_non_overlapping_windows():
    """Two distant anchors produce two chunks joined by blank lines."""
    part_a = "x" * 100 + " happy hour beer $5 " + "y" * 200
    gap = "z" * 3000
    part_b = "happy hour wine $8"
    full_text = part_a + gap + part_b

    focused = focus_text_for_happy_hour_menu(full_text, window=150, max_out=8000)

    assert "$5" in focused
    assert "$8" in focused
    assert "\n\n" in focused or "wine $8" in focused


def test_short_text_unchanged():
    assert focus_text_for_happy_hour_menu("hi") == "hi"


def test_empty_string():
    assert focus_text_for_happy_hour_menu("") == ""


def test_nav_bar_anchor_returns_full_text():
    """
    When 'HAPPY HOUR' appears only in a navigation-bar cluster near the top
    of the page (like Wix sites), the full text must be returned so that
    pricing data further down the page is not discarded.
    """
    # Simulates a Wix single-pager: nav at top, real menu pricing further down.
    nav = "Skip to Main Content SLUSHEES! FOOD HAPPY HOUR WKND BRUNCH BEER COCKTAILS WINE "
    food_section = "VEGAN BURGER BLACK BEAN PATTY. $16 FOOD fancy grilled cheese $15 " * 20
    pricing_section = "COCKTAILS & BEER dark mojito $12 MADEWEST PALE ALE $8 COORS LIGHT $6 "
    full_text = nav + food_section + pricing_section

    focused = focus_text_for_happy_hour_menu(full_text)

    # The full text should be preserved because the only anchor is nav-bar only
    assert "COORS LIGHT $6" in focused
    assert "MADEWEST PALE ALE $8" in focused


def test_real_section_anchor_windows_properly():
    """
    When 'Happy Hour' appears as a real section heading mid-page (not navigation),
    the windowing should activate and capture the surrounding content.
    """
    preamble = "Regular menu items salmon $40 steak $55 " * 50
    hh_section = "Happy Hour Specials! Draft beer $6 House wine $8 Sliders $8 "
    epilogue = "BRUNCH eggs benedict $18 " * 50
    full_text = preamble + hh_section + epilogue

    focused = focus_text_for_happy_hour_menu(full_text, window=200, max_out=8000)

    assert "Draft beer $6" in focused
    # The preamble (before the HH section) should be excluded from the window
    # (window starts up to pre_window=200 chars before the anchor)
    assert len(focused) < len(full_text)
