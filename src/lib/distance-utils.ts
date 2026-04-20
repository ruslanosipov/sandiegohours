import { HappyHourPlace } from '@/types/happy-hour';

/**
 * Calculate distance between two coordinates using Haversine formula
 * Returns distance in miles
 */
export function calculateDistance(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number
): number {
  const R = 3959; // Earth's radius in miles
  const dLat = toRadians(lat2 - lat1);
  const dLng = toRadians(lng2 - lng1);
  
  const a = 
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) *
    Math.sin(dLng / 2) * Math.sin(dLng / 2);
  
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  
  return R * c;
}

function toRadians(degrees: number): number {
  return degrees * (Math.PI / 180);
}

/**
 * Format distance for display
 * - Less than 0.1 miles: show in feet (e.g., "264 ft")
 * - 0.1 to 10 miles: show with 1 decimal (e.g., "0.5 mi")
 * - Over 10 miles: show as whole number (e.g., "12 mi")
 */
export function formatDistance(miles: number): string {
  if (miles < 0.1) {
    const feet = Math.round(miles * 5280);
    return `${feet} ft`;
  }
  
  if (miles < 10) {
    return `${miles.toFixed(1)} mi`;
  }
  
  return `${Math.round(miles)} mi`;
}

/**
 * Sort restaurants by distance from user location
 * Places without coordinates are sorted to the end
 * Returns new array with distance property added to each place
 */
export function sortByDistance(
  restaurants: HappyHourPlace[],
  userLat: number,
  userLng: number
): HappyHourPlace[] {
  const withDistance = restaurants.map(place => {
    if (place.latitude && place.longitude) {
      const distance = calculateDistance(
        userLat,
        userLng,
        parseFloat(place.latitude),
        parseFloat(place.longitude)
      );
      return { ...place, distance };
    }
    return { ...place, distance: Infinity };
  });

  return withDistance.sort((a, b) => {
    const distA = a.distance ?? Infinity;
    const distB = b.distance ?? Infinity;
    return distA - distB;
  });
}
