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
}

export interface ParsedHappyHour {
  day: string;
  startTime: string;
  endTime: string;
  isSecondSession?: boolean;
  startTime2?: string;
  endTime2?: string;
}
