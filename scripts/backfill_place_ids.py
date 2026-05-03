#!/usr/bin/env python3
"""
Add place_id to public/menu_data.csv and public/manual_overrides.csv by
matching restaurant_name to public/happy_hours.csv (unique match only).
Run from repo root: python scripts/backfill_place_ids.py
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
HAPPY = PUBLIC / "happy_hours.csv"
MENU = PUBLIC / "menu_data.csv"
OVERRIDES = PUBLIC / "manual_overrides.csv"

MENU_FIELDS = [
    "place_id",
    "restaurant_name",
    "cheapest_drink",
    "cheapest_drink_price",
    "cheapest_food",
    "cheapest_food_price",
    "menu_summary",
]

OVERRIDE_FIELDS = [
    "place_id",
    "restaurant_name",
    "happy_hour_times",
    "source",
    "freshness_date",
]


def load_name_to_place_ids() -> dict[str, list[str]]:
    by_name: dict[str, list[str]] = defaultdict(list)
    with open(HAPPY, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            name = (row.get("restaurant_name") or "").strip()
            pid = (row.get("place_id") or "").strip()
            if name and pid:
                by_name[name].append(pid)
    return dict(by_name)


def resolve_place_id(name: str, index: dict[str, list[str]]) -> str:
    name = name.strip()
    if not name:
        return ""
    ids = index.get(name) or []
    if not ids:
        print(f"  No place_id for name: {name!r}", file=sys.stderr)
        return ""
    if len(ids) > 1:
        print(
            f"  Ambiguous name {name!r} -> {len(ids)} place_ids; using first",
            file=sys.stderr,
        )
    return ids[0]


def backfill_menu(index: dict[str, list[str]]) -> None:
    if not MENU.exists():
        print("Skip menu_data.csv (missing)", file=sys.stderr)
        return
    with open(MENU, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("Skip menu_data.csv (empty)", file=sys.stderr)
        return
    out_rows = []
    for row in rows:
        name = (row.get("restaurant_name") or "").strip()
        pid = (row.get("place_id") or "").strip()
        if not pid:
            pid = resolve_place_id(name, index)
        out_rows.append(
            {
                "place_id": pid,
                "restaurant_name": row.get("restaurant_name", ""),
                "cheapest_drink": row.get("cheapest_drink", ""),
                "cheapest_drink_price": row.get("cheapest_drink_price", ""),
                "cheapest_food": row.get("cheapest_food", ""),
                "cheapest_food_price": row.get("cheapest_food_price", ""),
                "menu_summary": row.get("menu_summary", ""),
            }
        )
    with open(MENU, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MENU_FIELDS)
        w.writeheader()
        w.writerows(out_rows)
    print(f"Wrote {MENU} ({len(out_rows)} rows)")


def backfill_overrides(index: dict[str, list[str]]) -> None:
    if not OVERRIDES.exists():
        print("Skip manual_overrides.csv (missing)", file=sys.stderr)
        return
    with open(OVERRIDES, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("Skip manual_overrides.csv (empty)", file=sys.stderr)
        return
    out_rows = []
    for row in rows:
        name = (row.get("restaurant_name") or "").strip()
        pid = (row.get("place_id") or "").strip()
        if not pid:
            pid = resolve_place_id(name, index)
        out_rows.append(
            {
                "place_id": pid,
                "restaurant_name": row.get("restaurant_name", ""),
                "happy_hour_times": row.get("happy_hour_times", ""),
                "source": row.get("source", ""),
                "freshness_date": row.get("freshness_date", ""),
            }
        )
    with open(OVERRIDES, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OVERRIDE_FIELDS)
        w.writeheader()
        w.writerows(out_rows)
    print(f"Wrote {OVERRIDES} ({len(out_rows)} rows)")


def main() -> None:
    if not HAPPY.exists():
        print(f"Missing {HAPPY}", file=sys.stderr)
        sys.exit(1)
    index = load_name_to_place_ids()
    print(f"Loaded {len(index)} unique names from happy_hours.csv")
    backfill_menu(index)
    backfill_overrides(index)


if __name__ == "__main__":
    main()
