export interface HappyHourPlace {
  restaurant_name: string;
  address: string;
  phone_number: string;
  website_url: string;
  happy_hour_times: string;
  regular_hours: string;
  rating: string;
  review_count: string;
  price_level: string;
  source: string;
  freshness_date: string;
  latitude?: string;
  longitude?: string;
  place_id?: string;
  neighborhood?: string;
  distance?: number; // in miles, calculated at runtime
  // Google Maps data
  google_maps_url?: string;
  generative_summary?: string;
  // Menu data
  cheapest_drink?: string;
  cheapest_drink_price?: number;
  cheapest_food?: string;
  cheapest_food_price?: number;
  menu_summary?: string;
  menu_url?: string;
}

export interface ParsedHappyHour {
  day: string;
  startTime: string;
  endTime: string;
  isSecondSession?: boolean;
  startTime2?: string;
  endTime2?: string;
}
