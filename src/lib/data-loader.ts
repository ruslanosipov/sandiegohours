import { promises as fs } from "fs";
import path from "path";
import { parse } from "csv-parse/sync";

export interface RestaurantData {
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
  google_maps_url?: string;
  generative_summary?: string;
  cheapest_drink?: string;
  cheapest_drink_price?: number;
  cheapest_food?: string;
  cheapest_food_price?: number;
  menu_summary?: string;
}

interface MenuData {
  restaurant_name: string;
  cheapest_drink: string;
  cheapest_drink_price: string;
  cheapest_food: string;
  cheapest_food_price: string;
  menu_summary: string;
}

let cachedRestaurants: RestaurantData[] | null = null;

export function clearCache(): void {
  cachedRestaurants = null;
}

export async function getRestaurants(): Promise<RestaurantData[]> {
  if (cachedRestaurants) {
    return cachedRestaurants;
  }

  const csvPath = path.join(process.cwd(), "public", "happy_hours.csv");
  const fileContent = await fs.readFile(csvPath, "utf-8");

  const records = parse(fileContent, {
    columns: true,
    skip_empty_lines: true,
  }) as RestaurantData[];

  try {
    const menuCsvPath = path.join(process.cwd(), "public", "menu_data.csv");
    const menuContent = await fs.readFile(menuCsvPath, "utf-8");
    const menuRecords = parse(menuContent, {
      columns: true,
      skip_empty_lines: true,
    }) as MenuData[];

    const menuMap = new Map(menuRecords.map((m) => [m.restaurant_name, m]));

    for (const restaurant of records) {
      const menu = menuMap.get(restaurant.restaurant_name);
      if (menu) {
        restaurant.cheapest_drink = menu.cheapest_drink || undefined;
        restaurant.cheapest_drink_price = menu.cheapest_drink_price
          ? parseFloat(menu.cheapest_drink_price)
          : undefined;
        restaurant.cheapest_food = menu.cheapest_food || undefined;
        restaurant.cheapest_food_price = menu.cheapest_food_price
          ? parseFloat(menu.cheapest_food_price)
          : undefined;
        restaurant.menu_summary = menu.menu_summary || undefined;
      }
    }
  } catch {
    // Menu data is optional
  }

  cachedRestaurants = records;
  return records;
}
