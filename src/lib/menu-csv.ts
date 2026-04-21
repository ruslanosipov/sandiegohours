/**
 * Menu CSV utilities for cheapest happy hour items
 * Separate CSV format from main happy_hours.csv
 */

export interface MenuData {
  restaurant_name: string;
  cheapest_drink: string;
  cheapest_drink_price: number | null;
  cheapest_food: string;
  cheapest_food_price: number | null;
  all_drink_options: string[];
  all_food_options: string[];
}

/**
 * Generate concise summary like "$1 wings, $3 sliders, $5 bottled, $7 draft and cocktails"
 */
export function generateCheapestSummary(data: MenuData): string {
  const allOptions: string[] = [];
  
  // Add food options first (usually cheaper)
  allOptions.push(...data.all_food_options);
  
  // Add drink options
  allOptions.push(...data.all_drink_options);
  
  if (allOptions.length === 0) {
    return '';
  }
  
  // Sort by price (extract number after $)
  const sorted = allOptions.sort((a, b) => {
    const priceA = parseFloat(a.match(/\$([\d.]+)/)?.[1] || '0');
    const priceB = parseFloat(b.match(/\$([\d.]+)/)?.[1] || '0');
    return priceA - priceB;
  });
  
  // Join with commas, last item gets "and" if multiple
  if (sorted.length <= 2) {
    return sorted.join(' and ');
  }
  
  const last = sorted[sorted.length - 1];
  const rest = sorted.slice(0, -1);
  return `${rest.join(', ')} and ${last}`;
}

/**
 * Format MenuData as CSV row
 */
export function formatMenuCSV(data: MenuData): string {
  const summary = generateCheapestSummary(data);
  
  const fields = [
    data.restaurant_name,
    data.cheapest_drink,
    data.cheapest_drink_price?.toString() || '',
    data.cheapest_food,
    data.cheapest_food_price?.toString() || '',
    summary,
  ];
  
  // Escape fields containing commas
  return fields.map(field => {
    if (field.includes(',')) {
      return `"${field.replace(/"/g, '""')}"`;
    }
    return field;
  }).join(',');
}

/**
 * Parse CSV row to MenuData
 */
export function parseMenuCSV(csvLine: string): MenuData {
  const fields: string[] = [];
  let current = '';
  let inQuotes = false;
  
  for (const char of csvLine) {
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      fields.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  fields.push(current.trim());
  
  return {
    restaurant_name: fields[0] || '',
    cheapest_drink: fields[1] || '',
    cheapest_drink_price: fields[2] ? parseFloat(fields[2]) : null,
    cheapest_food: fields[3] || '',
    cheapest_food_price: fields[4] ? parseFloat(fields[4]) : null,
    all_drink_options: [], // Not stored in CSV, reconstructed from summary if needed
    all_food_options: [],
  };
}

/**
 * Get CSV header for menu data
 */
export function getMenuCSVHeader(): string {
  return 'restaurant_name,cheapest_drink,cheapest_drink_price,cheapest_food,cheapest_food_price,cheapest_options_summary';
}

/**
 * Update menu CSV file with new data
 */
export function updateMenuCSV(
  existingData: Map<string, MenuData>,
  newData: MenuData
): Map<string, MenuData> {
  const updated = new Map(existingData);
  updated.set(newData.restaurant_name, newData);
  return updated;
}

/**
 * Parse AI response to MenuData
 */
export function parseAIResponseToMenuData(
  restaurantName: string,
  aiResponse: { drink?: { name: string; price: number }; food?: { name: string; price: number } }
): MenuData {
  const drinkOptions: string[] = [];
  const foodOptions: string[] = [];
  
  if (aiResponse.drink) {
    drinkOptions.push(`$${aiResponse.drink.price} ${aiResponse.drink.name}`);
  }
  
  if (aiResponse.food) {
    foodOptions.push(`$${aiResponse.food.price} ${aiResponse.food.name}`);
  }
  
  return {
    restaurant_name: restaurantName,
    cheapest_drink: aiResponse.drink ? `$${aiResponse.drink.price} ${aiResponse.drink.name}` : '',
    cheapest_drink_price: aiResponse.drink?.price ?? null,
    cheapest_food: aiResponse.food ? `$${aiResponse.food.price} ${aiResponse.food.name}` : '',
    cheapest_food_price: aiResponse.food?.price ?? null,
    all_drink_options: drinkOptions,
    all_food_options: foodOptions,
  };
}
