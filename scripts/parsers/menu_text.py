"""
Narrow full-page menu text to regions likely to contain happy hour pricing.

Long-scrape pages (e.g. Wix with iframes) interleave regular wine lists and HH
deals. This is a cheap pre-filter before the LLM; it does not understand layout.
"""
import re
from typing import List, Tuple

# Triggers a window of surrounding text. Tuned to appear in real HH sections;
# "drink specials" can appear outside HH — prompt still enforces HH-only.
_ANCHOR_RES = [
    re.compile(r"happy\s*hour", re.IGNORECASE),
    re.compile(r"happy-hour", re.IGNORECASE),
    re.compile(r"\bhh\s+specials?\b", re.IGNORECASE),
    re.compile(r"\bhh\b", re.IGNORECASE),
    re.compile(r"drink\s+specials?", re.IGNORECASE),
    re.compile(r"appetizer\s+specials?", re.IGNORECASE),
]

# Pattern that indicates an anchor is inside a navigation/tab bar rather than
# a real content section.  A nav-bar typically has several short ALL-CAPS or
# Title-Case words separated only by spaces or single special chars within a
# short (~120 char) span (e.g. "FOOD HAPPY HOUR WKND BRUNCH BEER COCKTAILS").
_NAV_BAR_RE = re.compile(
    r"(?:(?:[A-Z][A-Za-z&]+|[A-Z]{2,})\s+){3,}(?:[A-Z][A-Za-z&]+|[A-Z]{2,})"
)

# A real HH section needs at least one item with a dollar-amount price within
# the scan window.
_PRICE_RE = re.compile(r"\$\s*\d+|\d+\s*(?:bucks?|dollars?)", re.IGNORECASE)

_DEFAULT_WINDOW = 4000
# Context to include BEFORE each anchor so the header/intro line is captured
_DEFAULT_PRE_WINDOW = 200
_DEFAULT_MAX_OUT = 8000

# When the "HAPPY HOUR" anchor appears at the very top of the page (within
# this fraction of total text length), check if it looks like a nav-bar entry.
# If it does, skip windowing entirely so the full text is preserved.
_NAV_TOP_FRACTION = 0.10


def _merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    out: List[Tuple[int, int]] = [intervals[0]]
    for s, e in intervals[1:]:
        ps, pe = out[-1]
        if s <= pe:
            out[-1] = (ps, max(pe, e))
        else:
            out.append((s, e))
    return out


def _is_nav_bar_anchor(full_text: str, match_start: int, scan: int = 120) -> bool:
    """Return True if the anchor appears inside a navigation-bar cluster."""
    n = len(full_text)
    region = full_text[max(0, match_start - scan): min(n, match_start + scan)]
    return bool(_NAV_BAR_RE.search(region))


def focus_text_for_happy_hour_menu(
    full_text: str,
    window: int = _DEFAULT_WINDOW,
    pre_window: int = _DEFAULT_PRE_WINDOW,
    max_out: int = _DEFAULT_MAX_OUT,
) -> str:
    """
    Return a substring of ``full_text`` centered on happy-hour-like anchors.

    For each regex match, take up to ``pre_window`` characters **before** the
    match and up to ``window`` characters **after** it.  Overlapping ranges are
    merged.  Non-overlapping ranges are joined with blank lines.  Total length
    is capped at ``max_out``.

    Navigation-bar detection: if ALL anchor matches are inside a nav-bar
    cluster near the top of the page (first ``_NAV_TOP_FRACTION`` of the text),
    windowing is skipped and the full text is returned.  This prevents the
    filter from discarding pricing data that lives below the navigation.

    If no anchor matches, returns ``full_text`` unchanged.
    """
    if not full_text:
        return full_text
    n = len(full_text)
    if n <= 200:
        return full_text

    matches: List[Tuple[int, int]] = []  # (match_start, is_nav)
    for rx in _ANCHOR_RES:
        for m in rx.finditer(full_text):
            is_nav = (
                m.start() < n * _NAV_TOP_FRACTION
                and _is_nav_bar_anchor(full_text, m.start())
            )
            matches.append((m.start(), is_nav))

    if not matches:
        return full_text

    # If every anchor match looks like a nav-bar entry, preserve the full text
    # so pricing content further down the page is not cut off.
    all_nav = all(is_nav for _, is_nav in matches)
    if all_nav:
        return full_text

    intervals: List[Tuple[int, int]] = []
    for match_start, is_nav in matches:
        if is_nav:
            # Nav-bar anchors don't make good window centers; skip them.
            continue
        s = max(0, match_start - pre_window)
        e = min(n, match_start + window)
        intervals.append((s, e))

    if not intervals:
        # All remaining anchors were nav-bar; fall back to full text.
        return full_text

    merged = _merge_intervals(intervals)
    parts = [full_text[s:e] for s, e in merged]
    out = "\n\n".join(parts)
    if len(out) > max_out:
        out = out[:max_out]
    return out
