export interface Neighborhood {
  id: string;
  label: string;
  south: number;
  west: number;
  north: number;
  east: number;
}

export const NEIGHBORHOODS: Neighborhood[] = [
  { id: 'north_park', label: 'North Park', south: 32.745, west: -117.135, north: 32.755, east: -117.115 },
  { id: 'south_park', label: 'South Park', south: 32.720, west: -117.135, north: 32.745, east: -117.115 },
  { id: 'normal_heights', label: 'Normal Heights', south: 32.755, west: -117.135, north: 32.775, east: -117.115 },
  { id: 'hillcrest', label: 'Hillcrest', south: 32.735, west: -117.170, north: 32.760, east: -117.145 },
  { id: 'little_italy', label: 'Little Italy', south: 32.715, west: -117.170, north: 32.730, east: -117.155 },
  { id: 'gaslamp', label: 'Gaslamp', south: 32.705, west: -117.165, north: 32.720, east: -117.155 },
  { id: 'pacific_beach', label: 'Pacific Beach', south: 32.785, west: -117.260, north: 32.805, east: -117.230 },
  { id: 'ocean_beach', label: 'Ocean Beach', south: 32.735, west: -117.260, north: 32.755, east: -117.235 },
  { id: 'mission_valley', label: 'Mission Valley', south: 32.755, west: -117.200, north: 32.775, east: -117.170 },
  { id: 'clairemont', label: 'Clairemont', south: 32.790, west: -117.210, north: 32.815, east: -117.180 },
  { id: 'convoy', label: 'Convoy', south: 32.820, west: -117.160, north: 32.835, east: -117.140 },
  { id: 'la_jolla', label: 'La Jolla', south: 32.830, west: -117.280, north: 32.860, east: -117.240 },
  { id: 'utc', label: 'UTC', south: 32.860, west: -117.240, north: 32.880, east: -117.220 },
];

export function getNeighborhoodId(lat: number, lng: number): string | undefined {
  for (const n of NEIGHBORHOODS) {
    if (lat >= n.south && lat <= n.north && lng >= n.west && lng <= n.east) {
      return n.id;
    }
  }
  return undefined;
}

export function getNeighborhoodLabel(id: string): string {
  return NEIGHBORHOODS.find((n) => n.id === id)?.label ?? id;
}
