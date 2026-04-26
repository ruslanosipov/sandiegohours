"""
Tests for adaptive grid generator and type filtering.
"""
import pytest
from scripts.fetchers.grid import (
    GridCell,
    subdivide_cell,
    should_subdivide,
    generate_grid,
    get_keywords_for_cell,
    should_exclude_place,
    get_all_preset_names,
    NEIGHBORHOOD_PRESETS,
    MIN_CELL_SIZE_MILES,
    RESULTS_CAP,
    TIER1_KEYWORDS,
    TIER2_KEYWORDS,
    DEFAULT_BBOX,
)


class TestGridCell:
    def test_creation(self):
        cell = GridCell(south=32.7, west=-117.2, north=32.8, east=-117.1)
        assert cell.south == 32.7
        assert cell.east == -117.1

    def test_center(self):
        cell = GridCell(south=32.7, west=-117.2, north=32.9, east=-117.0)
        lat, lng = cell.center
        assert lat == pytest.approx(32.8)
        assert lng == pytest.approx(-117.1)

    def test_width_miles(self):
        cell = GridCell(south=32.7, west=-117.2, north=32.8, east=-117.1)
        # 0.1 degrees lng at ~32.7N ≈ 5.8 miles
        assert cell.width_miles() == pytest.approx(5.8, rel=0.1)

    def test_height_miles(self):
        cell = GridCell(south=32.7, west=-117.2, north=32.8, east=-117.1)
        # 0.1 degrees lat ≈ 6.9 miles
        assert cell.height_miles() == pytest.approx(6.9, rel=0.1)

    def test_to_location_restriction(self):
        cell = GridCell(south=32.7, west=-117.2, north=32.8, east=-117.1)
        restriction = cell.to_location_restriction()
        assert "rectangle" in restriction
        assert restriction["rectangle"]["low"]["latitude"] == 32.7
        assert restriction["rectangle"]["high"]["longitude"] == -117.1


class TestSubdivideCell:
    def test_creates_four_quadrants(self):
        cell = GridCell(south=32.7, west=-117.2, north=32.9, east=-117.0)
        children = subdivide_cell(cell)
        assert len(children) == 4

    def test_quadrants_cover_parent_with_overlap(self):
        cell = GridCell(south=32.7, west=-117.2, north=32.9, east=-117.0)
        children = subdivide_cell(cell)
        # With 7.5% overlap, children should slightly exceed parent bounds
        lats = [c.south for c in children] + [c.north for c in children]
        lngs = [c.west for c in children] + [c.east for c in children]
        assert min(lats) <= cell.south
        assert max(lats) >= cell.north
        assert min(lngs) <= cell.west
        assert max(lngs) >= cell.east

    def test_quadrants_are_smaller(self):
        cell = GridCell(south=32.7, west=-117.2, north=32.9, east=-117.0)
        children = subdivide_cell(cell)
        for child in children:
            assert child.width_miles() < cell.width_miles()
            assert child.height_miles() < cell.height_miles()


class TestShouldSubdivide:
    def test_no_subdivide_when_under_cap(self):
        cell = GridCell(south=32.7, west=-117.2, north=32.9, east=-117.0)
        assert should_subdivide(cell, RESULTS_CAP - 1) is False
        assert should_subdivide(cell, 10) is False

    def test_subdivide_when_at_cap_and_large(self):
        cell = GridCell(south=32.7, west=-117.2, north=32.9, east=-117.0)
        assert should_subdivide(cell, RESULTS_CAP) is True

    def test_no_subdivide_when_at_cap_but_too_small(self):
        tiny = GridCell(
            south=32.7,
            west=-117.2,
            north=32.7 + MIN_CELL_SIZE_MILES / 69.0,
            east=-117.2 + MIN_CELL_SIZE_MILES / 58.0,
        )
        assert should_subdivide(tiny, RESULTS_CAP) is False


class TestGenerateGrid:
    def test_single_cell(self):
        cell = GridCell(south=32.7, west=-117.2, north=32.8, east=-117.1)
        result = generate_grid(cell=cell)
        assert len(result) == 1
        assert result[0] == cell

    def test_preset(self):
        result = generate_grid(preset="north_park")
        assert len(result) == 1
        assert result[0] == NEIGHBORHOOD_PRESETS["north_park"]

    def test_preset_all_available(self):
        presets = get_all_preset_names()
        assert "north_park" in presets
        assert "convoy" in presets
        assert "la_jolla" in presets
        for name in presets:
            result = generate_grid(preset=name)
            assert len(result) == 1

    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            generate_grid(preset="nonexistent")

    def test_custom_bbox(self):
        bbox = {"south": 32.7, "west": -117.2, "north": 32.8, "east": -117.1}
        result = generate_grid(bbox=bbox)
        assert len(result) == 1
        assert result[0].south == 32.7

    def test_default_bbox(self):
        result = generate_grid()
        assert len(result) == 1
        assert result[0].south == DEFAULT_BBOX["south"]


class TestGetKeywordsForCell:
    def test_tier1_only(self):
        cell = GridCell(south=32.7, west=-117.2, north=32.8, east=-117.1)
        kw = get_keywords_for_cell(cell, tier1_only=True)
        assert set(kw) == set(TIER1_KEYWORDS)

    def test_all_keywords(self):
        cell = GridCell(south=32.7, west=-117.2, north=32.8, east=-117.1)
        kw = get_keywords_for_cell(cell)
        assert set(TIER1_KEYWORDS).issubset(set(kw))
        assert set(TIER2_KEYWORDS).issubset(set(kw))


class TestShouldExcludePlace:
    def test_exclude_pure_cafe(self):
        assert should_exclude_place(["cafe", "coffee_shop"]) is True

    def test_exclude_gas_station(self):
        assert should_exclude_place(["gas_station", "convenience_store"]) is True

    def test_keep_bar(self):
        assert should_exclude_place(["bar", "restaurant"]) is False

    def test_keep_mixed(self):
        # cafe + restaurant should NOT be excluded (has non-excluded type)
        assert should_exclude_place(["cafe", "restaurant"]) is False

    def test_empty_types(self):
        assert should_exclude_place([]) is False

    def test_none_types(self):
        assert should_exclude_place(None) is False

    def test_case_insensitive(self):
        assert should_exclude_place(["CAFE", "BAKERY"]) is True
        assert should_exclude_place(["BAR", "CAFE"]) is False
