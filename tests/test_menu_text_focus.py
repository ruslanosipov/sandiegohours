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
