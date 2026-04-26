"""
Adaptive grid generator for San Diego coverage with neighborhood presets.

Uses quadtree subdivision to ensure no cell returns the 60-result truncation cap.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class GridCell:
    """A rectangular search cell."""
    south: float
    west: float
    north: float
    east: float

    @property
    def center(self) -> tuple:
        return ((self.south + self.north) / 2, (self.west + self.east) / 2)

    def to_location_restriction(self) -> dict:
        return {
            "rectangle": {
                "low": {"latitude": self.south, "longitude": self.west},
                "high": {"latitude": self.north, "longitude": self.east},
            }
        }

    def width_miles(self) -> float:
        # Approximate: 1 degree lng at ~32.7N lat ≈ 58 miles
        return (self.east - self.west) * 58.0

    def height_miles(self) -> float:
        # 1 degree lat ≈ 69 miles
        return (self.north - self.south) * 69.0


# Bounding box: North of Division St, West of ~I-15, South of UCSD
# Loose bounding box to cover all relevant SD areas
DEFAULT_BBOX = {
    "south": 32.64,   # Division St area
    "west": -117.28,  # Pacific Coast
    "north": 32.88,   # UCSD / Torrey Pines
    "east": -117.08,  # ~54th St / I-15
}

# Minimum cell size in miles before we stop subdividing
MIN_CELL_SIZE_MILES = 0.75

# Overlap factor to avoid seam dropping (15%)
OVERLAP_FACTOR = 0.075

# Google Places Text Search hard cap
RESULTS_CAP = 60

# Tier 1 keywords: used for truncation detection
TIER1_KEYWORDS = ["restaurant", "bar", "happy hour"]

# Tier 2 keywords: gap fillers, run only on finalized cells
TIER2_KEYWORDS = [
    "pub", "brewery", "gastropub", "cocktail bar", "wine bar",
    "sports bar", "lounge", "taproom", "distillery",
    "seafood restaurant", "steakhouse", "sushi restaurant",
    "mexican restaurant", "italian restaurant", "american restaurant",
    "thai restaurant", "burgers", "bbq", "pizza",
]

# Types to exclude before Place Details (coffee shops, gas stations, etc.)
EXCLUDED_TYPES = {
    "cafe", "coffee_shop", "bakery", "gas_station",
    "convenience_store", "supermarket", "grocery_store",
    "pharmacy", "bank", "atm", "park", "school",
    "hospital", "car_repair", "parking", "library",
    "place_of_worship", "local_government_office", "museum",
}

# Neighborhood presets (south, west, north, east)
NEIGHBORHOOD_PRESETS: Dict[str, GridCell] = {
    "north_park": GridCell(32.745, -117.135, 32.770, -117.115),
    "south_park": GridCell(32.720, -117.135, 32.745, -117.115),
    "normal_heights": GridCell(32.755, -117.135, 32.775, -117.115),
    "hillcrest": GridCell(32.735, -117.170, 32.760, -117.145),
    "little_italy": GridCell(32.715, -117.170, 32.730, -117.155),
    "gaslamp": GridCell(32.705, -117.165, 32.720, -117.155),
    "pacific_beach": GridCell(32.785, -117.260, 32.805, -117.230),
    "ocean_beach": GridCell(32.735, -117.260, 32.755, -117.235),
    "mission_valley": GridCell(32.755, -117.200, 32.775, -117.170),
    "clairemont": GridCell(32.790, -117.210, 32.815, -117.180),
    "convoy": GridCell(32.820, -117.160, 32.835, -117.140),  # Kearny Mesa / Convoy
    "la_jolla": GridCell(32.830, -117.280, 32.860, -117.240),
    "utc": GridCell(32.860, -117.240, 32.880, -117.220),
}


def subdivide_cell(cell: GridCell) -> List[GridCell]:
    """Split a cell into 4 quadrants with slight overlap."""
    mid_lat = (cell.south + cell.north) / 2
    mid_lng = (cell.west + cell.east) / 2
    lat_overlap = (cell.north - cell.south) * OVERLAP_FACTOR
    lng_overlap = (cell.east - cell.west) * OVERLAP_FACTOR

    return [
        GridCell(cell.south, cell.west, mid_lat + lat_overlap, mid_lng + lng_overlap),
        GridCell(cell.south, mid_lng - lng_overlap, mid_lat + lat_overlap, cell.east),
        GridCell(mid_lat - lat_overlap, cell.west, cell.north, mid_lng + lng_overlap),
        GridCell(mid_lat - lat_overlap, mid_lng - lng_overlap, cell.north, cell.east),
    ]


def should_subdivide(cell: GridCell, result_count: int) -> bool:
    """Determine if a cell needs subdivision based on truncation."""
    if result_count < RESULTS_CAP:
        return False
    if cell.width_miles() <= MIN_CELL_SIZE_MILES or cell.height_miles() <= MIN_CELL_SIZE_MILES:
        return False
    return True


def generate_grid(
    bbox: Optional[dict] = None,
    preset: Optional[str] = None,
    cell: Optional[GridCell] = None,
) -> List[GridCell]:
    """
    Generate search grid.

    Args:
        bbox: Custom bounding box dict with south/west/north/east
        preset: Neighborhood preset name
        cell: Single custom cell

    Returns:
        List of grid cells to search
    """
    if cell:
        return [cell]
    if preset:
        if preset not in NEIGHBORHOOD_PRESETS:
            raise ValueError(
                f"Unknown preset '{preset}'. Available: {list(NEIGHBORHOOD_PRESETS.keys())}"
            )
        return [NEIGHBORHOOD_PRESETS[preset]]

    bounds = bbox or DEFAULT_BBOX
    initial = GridCell(
        south=bounds["south"],
        west=bounds["west"],
        north=bounds["north"],
        east=bounds["east"],
    )
    return [initial]


def get_keywords_for_cell(cell: GridCell, tier1_only: bool = False) -> List[str]:
    """
    Return keywords to use for a given cell.
    Tier 1 is always used. Tier 2 is used unless tier1_only is set.
    In practice, tier2 keywords are run after the cell is finalized
    (i.e., not truncated).
    """
    if tier1_only:
        return list(TIER1_KEYWORDS)
    return list(TIER1_KEYWORDS) + list(TIER2_KEYWORDS)


def should_exclude_place(place_types: List[str]) -> bool:
    """
    Check if a place should be excluded based on its types.
    Returns True if the place has ONLY excluded types (no bar, restaurant, etc.)
    """
    if not place_types:
        return False  # Be conservative if no types

    place_type_set = set(t.lower() for t in place_types)

    # If any type is not in the excluded set, keep it
    if not place_type_set.issubset(EXCLUDED_TYPES):
        return False

    # All types are excluded
    return True


def get_all_preset_names() -> List[str]:
    """Return list of available neighborhood preset names."""
    return list(NEIGHBORHOOD_PRESETS.keys())
