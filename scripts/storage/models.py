"""
Data models for the happy hour pipeline.
"""
from dataclasses import dataclass, field, fields
from typing import Optional, List
from datetime import datetime


@dataclass
class Restaurant:
    """Core restaurant data."""
    restaurant_name: str
    address: str
    phone_number: str = ""
    website_url: str = ""
    happy_hour_times: str = ""
    regular_hours: str = ""
    rating: str = ""
    review_count: str = ""
    price_level: str = ""
    source: str = ""
    freshness_date: str = ""
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    
    # Menu data (populated by AI)
    cheapest_drink: Optional[str] = None
    cheapest_drink_price: Optional[float] = None
    cheapest_food: Optional[str] = None
    cheapest_food_price: Optional[float] = None
    menu_summary: Optional[str] = None


@dataclass
class MenuData:
    """Menu data extracted by AI."""
    restaurant_name: str
    cheapest_drink: str = ""
    cheapest_drink_price: Optional[float] = None
    cheapest_food: str = ""
    cheapest_food_price: Optional[float] = None
    menu_summary: str = ""


@dataclass
class ProcessingState:
    """Track pipeline progress for resume support."""
    step: str
    completed_restaurants: List[str] = field(default_factory=list)
    failed_restaurants: List[str] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            'step': self.step,
            'completed_restaurants': self.completed_restaurants,
            'failed_restaurants': self.failed_restaurants,
            'last_updated': self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ProcessingState':
        return cls(
            step=data.get('step', ''),
            completed_restaurants=data.get('completed_restaurants', []),
            failed_restaurants=data.get('failed_restaurants', []),
            last_updated=data.get('last_updated', datetime.now().isoformat())
        )


@dataclass
class HappyHourSchedule:
    """Parsed happy hour schedule."""
    day: str
    times: str
    is_closed: bool = False
