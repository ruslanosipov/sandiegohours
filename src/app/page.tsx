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
}

async function getRestaurants(): Promise<Restaurant[]> {
  const csvPath = path.join(process.cwd(), 'public', 'happy_hours.csv');
  const fileContent = await fs.readFile(csvPath, 'utf-8');
  
  const records = parse(fileContent, {
    columns: true,
    skip_empty_lines: true,
  }) as Restaurant[];
  
  return records;
}

export default async function Home() {
  const restaurants = await getRestaurants();
  
  return (
    <main className="min-h-screen bg-gray-50">
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white py-12">
        <div className="max-w-6xl mx-auto px-4">
          <h1 className="text-4xl font-bold mb-2">92116 Happy Hour Finder</h1>
          <p className="text-lg opacity-90">Find the best happy hours in Normal Heights, North Park & surrounding areas</p>
        </div>
      </div>
      
      <div className="max-w-6xl mx-auto px-4 py-8">
        <HappyHourFinder restaurants={restaurants} />
      </div>
    </main>
  );
}
