"""
Narrow full-page menu text to regions likely to contain happy hour pricing.

Long-scrape pages (e.g. Wix with iframes) interleave regular wine lists and HH
deals. This is a cheap pre-filter before the LLM; it does not understand layout.
"""
import re
from typing import List, Tuple

# Triggers a window of following text. Tuned to appear in real HH sections;
# "drink specials" can appear outside HH — prompt still enforces HH-only.
_ANCHOR_RES = [
    re.compile(r"happy\s*hour", re.IGNORECASE),
    re.compile(r"happy-hour", re.IGNORECASE),
    re.compile(r"\bhh\s+specials?\b", re.IGNORECASE),
    re.compile(r"\bhh\b", re.IGNORECASE),
    re.compile(r"drink\s+specials?", re.IGNORECASE),
    re.compile(r"appetizer\s+specials?", re.IGNORECASE),
]

_DEFAULT_WINDOW = 4000
_DEFAULT_MAX_OUT = 8000


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


def focus_text_for_happy_hour_menu(
    full_text: str,
    window: int = _DEFAULT_WINDOW,
    max_out: int = _DEFAULT_MAX_OUT,
) -> str:
    """
    Return a substring of ``full_text`` centered on happy-hour-like anchors.

    For each regex match, take up to ``window`` characters starting at the
    match. Overlapping ranges are merged. Non-overlapping ranges are joined
    with blank lines. Total length is capped at ``max_out``.

    If no anchor matches, returns ``full_text`` unchanged (same behavior as
    before this filter for sites that never say "happy hour" in text).
    """
    if not full_text:
        return full_text
    n = len(full_text)
    if n <= 200:
        return full_text

    intervals: List[Tuple[int, int]] = []
    for rx in _ANCHOR_RES:
        for m in rx.finditer(full_text):
            s = m.start()
            e = min(n, s + window)
            intervals.append((s, e))

    if not intervals:
        return full_text

    merged = _merge_intervals(intervals)
    parts = [full_text[s:e] for s, e in merged]
    out = "\n\n".join(parts)
    if len(out) > max_out:
        out = out[:max_out]
    return out
