import { promises as fs } from 'fs';
import path from 'path';
import { parse } from 'csv-parse/sync';
import HappyHourFinder from './components/HappyHourFinder';
import { getNeighborhoodId } from './data/neighborhoods';

interface Restaurant {
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
  neighborhood?: string;
  place_id?: string;
  google_maps_url?: string;
  generative_summary?: string;
  cheapest_drink?: string;
  cheapest_drink_price?: number;
  cheapest_food?: string;
  cheapest_food_price?: number;
  menu_summary?: string;
}

interface MenuData {
  place_id?: string;
  restaurant_name: string;
  cheapest_drink: string;
  cheapest_drink_price: string;
  cheapest_food: string;
  cheapest_food_price: string;
  menu_summary: string;
}

interface OverrideRow {
  place_id?: string;
  restaurant_name: string;
  happy_hour_times?: string;
  source?: string;
  freshness_date?: string;
}

/** Lookup overrides by Google place_id first, then by restaurant_name. */
async function loadOverrides(): Promise<{
  byPlaceId: Map<string, OverrideRow>;
  byName: Map<string, OverrideRow>;
}> {
  const overridesPath = path.join(process.cwd(), 'public', 'manual_overrides.csv');
  const maps = {
    byPlaceId: new Map<string, OverrideRow>(),
    byName: new Map<string, OverrideRow>(),
  };
  try {
    const content = await fs.readFile(overridesPath, 'utf-8');
    const rows = parse(content, {
      columns: true,
      skip_empty_lines: true,
      trim: true,
    }) as OverrideRow[];
    for (const r of rows) {
      if (!r.restaurant_name) {
        continue;
      }
      maps.byName.set(r.restaurant_name, r);
      const pid = r.place_id?.trim();
      if (pid) {
        maps.byPlaceId.set(pid, r);
      }
    }
    return maps;
  } catch {
    return maps;
  }
}

async function getRestaurants(): Promise<Restaurant[]> {
  const csvPath = path.join(process.cwd(), 'public', 'happy_hours.csv');
  const fileContent = await fs.readFile(csvPath, 'utf-8');

  const records = parse(fileContent, {
    columns: true,
    skip_empty_lines: true,
  }) as Restaurant[];

  // Apply manual overrides (kept out of the upstream CSV so they survive re-fetches)
  const overrides = await loadOverrides();
  for (const restaurant of records) {
    const pid = restaurant.place_id?.trim();
    const override =
      (pid && overrides.byPlaceId.get(pid)) ||
      overrides.byName.get(restaurant.restaurant_name);
    if (override?.happy_hour_times) {
      restaurant.happy_hour_times = override.happy_hour_times;
      restaurant.source = override.source || 'Manual Override';
      if (override.freshness_date) {
        restaurant.freshness_date = override.freshness_date;
      }
    }
  }

  // Assign neighborhoods based on lat/lng
  for (const restaurant of records) {
    const lat = parseFloat(restaurant.latitude ?? '');
    const lng = parseFloat(restaurant.longitude ?? '');
    if (!isNaN(lat) && !isNaN(lng)) {
      restaurant.neighborhood = getNeighborhoodId(lat, lng);
    }
  }

  try {
    const menuCsvPath = path.join(process.cwd(), 'public', 'menu_data.csv');
    const menuContent = await fs.readFile(menuCsvPath, 'utf-8');
    const menuRecords = parse(menuContent, {
      columns: true,
      skip_empty_lines: true,
    }) as MenuData[];

    const menuByPlaceId = new Map<string, MenuData>();
    const menuByName = new Map<string, MenuData>();
    for (const m of menuRecords) {
      menuByName.set(m.restaurant_name, m);
      const mid = m.place_id?.trim();
      if (mid) {
        menuByPlaceId.set(mid, m);
      }
    }

    for (const restaurant of records) {
      const pid = restaurant.place_id?.trim();
      const menu =
        (pid && menuByPlaceId.get(pid)) ||
        menuByName.get(restaurant.restaurant_name);
      if (menu) {
        restaurant.cheapest_drink = menu.cheapest_drink || undefined;
        restaurant.cheapest_drink_price = menu.cheapest_drink_price ? parseFloat(menu.cheapest_drink_price) : undefined;
        restaurant.cheapest_food = menu.cheapest_food || undefined;
        restaurant.cheapest_food_price = menu.cheapest_food_price ? parseFloat(menu.cheapest_food_price) : undefined;
        restaurant.menu_summary = menu.menu_summary || undefined;
      }
    }
  } catch (error) {
    console.log('Menu data not loaded yet:', error);
  }

  return records;
}

export default async function Home() {
  const restaurants = await getRestaurants();

  return (
    <main className="min-h-screen bg-white">
      {/* Banner */}
      <div className="bg-white py-6 md:py-10">
        <div className="max-w-6xl mx-auto px-4 flex justify-center">
          <img
            src="/banner.png"
            alt="North Park Happy Hour"
            className="w-full max-w-2xl h-auto"
          />
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 pb-12">
        <HappyHourFinder restaurants={restaurants} />
      </div>
    </main>
  );
}
