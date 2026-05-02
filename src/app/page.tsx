import { getRestaurants } from "@/lib/data-loader";
import HappyHourFinder from "./components/HappyHourFinder";
import { getNeighborhoodId } from "./data/neighborhoods";

export default async function Home() {
  const restaurants = await getRestaurants();

  // Assign neighborhoods based on lat/lng
  for (const restaurant of restaurants) {
    const lat = parseFloat(restaurant.latitude ?? '');
    const lng = parseFloat(restaurant.longitude ?? '');
    if (!isNaN(lat) && !isNaN(lng)) {
      restaurant.neighborhood = getNeighborhoodId(lat, lng);
    }
  }

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
