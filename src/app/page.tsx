import { promises as fs } from 'fs';
import path from 'path';
import { parse } from 'csv-parse/sync';
import HappyHourFinder from './components/HappyHourFinder';

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

async function getRestaurants(): Promise<Restaurant[]> {
  // Load main restaurant data
  const csvPath = path.join(process.cwd(), 'public', 'happy_hours.csv');
  const fileContent = await fs.readFile(csvPath, 'utf-8');
  
  const records = parse(fileContent, {
    columns: true,
    skip_empty_lines: true,
  }) as Restaurant[];
  
  // Load menu data
  try {
    const menuCsvPath = path.join(process.cwd(), 'public', 'menu_data.csv');
    const menuContent = await fs.readFile(menuCsvPath, 'utf-8');
    const menuRecords = parse(menuContent, {
      columns: true,
      skip_empty_lines: true,
    }) as MenuData[];
    
    // Create lookup map for menu data
    const menuMap = new Map(menuRecords.map(m => [m.restaurant_name, m]));
    
    // Merge menu data into restaurants
    for (const restaurant of records) {
      const menu = menuMap.get(restaurant.restaurant_name);
      if (menu) {
        restaurant.cheapest_drink = menu.cheapest_drink || undefined;
        restaurant.cheapest_drink_price = menu.cheapest_drink_price ? parseFloat(menu.cheapest_drink_price) : undefined;
        restaurant.cheapest_food = menu.cheapest_food || undefined;
        restaurant.cheapest_food_price = menu.cheapest_food_price ? parseFloat(menu.cheapest_food_price) : undefined;
        restaurant.menu_summary = menu.menu_summary || undefined;
      }
    }
  } catch (error) {
    // menu_data.csv might not exist yet
    console.log('Menu data not loaded yet:', error);
  }
  
  return records;
}

export default async function Home() {
  const restaurants = await getRestaurants();
  
  return (
    <main className="min-h-screen bg-brand-cream">
      {/* Banner */}
      <div className="bg-brand-teal py-8">
        <div className="max-w-4xl mx-auto px-4">
          <img 
            src="/banner.jpg" 
            alt="San Diego Happy Hour" 
            className="w-full max-w-2xl mx-auto rounded-lg shadow-lg"
          />
        </div>
      </div>
      
      {/* Tagline */}
      <div className="bg-brand-yellow py-4">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <p className="text-lg text-brand-teal font-semibold">
            Find the best happy hours in Normal Heights, North Park & surrounding areas
          </p>
        </div>
      </div>
      
      <div className="max-w-6xl mx-auto px-4 py-8">
        <HappyHourFinder restaurants={restaurants} />
      </div>
    </main>
  );
}
