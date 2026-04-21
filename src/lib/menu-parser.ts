import { HappyHourPlace } from '@/types/happy-hour';

export interface MenuItem {
  name: string;
  price: number | null;
  category: 'drink' | 'food';
}

export interface CheapestItems {
  cheapestDrink: { name: string; price: number } | null;
  cheapestFood: { name: string; price: number } | null;
}

/**
 * Extract cheapest drink and food from parsed menu items
 */
export function extractCheapestItems(items: MenuItem[]): CheapestItems {
  const drinks = items.filter(i => i.category === 'drink' && i.price !== null);
  const foods = items.filter(i => i.category === 'food' && i.price !== null);

  const cheapestDrink = drinks.length > 0
    ? drinks.reduce((min, item) => item.price! < min.price! ? item : min)
    : null;

  const cheapestFood = foods.length > 0
    ? foods.reduce((min, item) => item.price! < min.price! ? item : min)
    : null;

  return {
    cheapestDrink: cheapestDrink ? { name: cheapestDrink.name, price: cheapestDrink.price! } : null,
    cheapestFood: cheapestFood ? { name: cheapestFood.name, price: cheapestFood.price! } : null,
  };
}

interface AIResponse {
  drink?: { name: string; price: number };
  food?: { name: string; price: number };
  menuItems?: MenuItem[];
}

/**
 * Call OpenRouter API to parse menu from website
 */
export async function parseMenuWithAI(
  restaurantName: string,
  menuUrl: string,
  apiKey: string
): Promise<CheapestItems | null> {
  try {
    // Fetch menu HTML
    const response = await fetch(menuUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      },
    });
    
    if (!response.ok) {
      console.error(`Failed to fetch menu: ${response.status}`);
      return null;
    }

    const html = await response.text();
    
    // Extract text from HTML (basic cleanup)
    const textContent = html
      .replace(/<script[^>]*>.*?<\/script>/gi, '')
      .replace(/<style[^>]*>.*?<\/style>/gi, '')
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .slice(0, 8000); // Limit content length

    // Call OpenRouter API
    const aiResponse = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: 'google/gemma-3-4b-it:free',
        messages: [
          {
            role: 'system',
            content: 'You are a menu parser. Extract happy hour drink and food items with prices. Return JSON only.',
          },
          {
            role: 'user',
            content: `Parse this menu from ${restaurantName} and find the cheapest happy hour drink and cheapest happy hour food item. 

Menu content:
${textContent}

Return JSON in this exact format:
{
  "drink": {"name": "Drink Name", "price": 5.00},
  "food": {"name": "Food Name", "price": 6.00}
}

If no prices found, use null. Only include happy hour items.`,
          },
        ],
        temperature: 0.1,
      }),
    });

    if (!aiResponse.ok) {
      console.error(`AI API error: ${aiResponse.status}`);
      return null;
    }

    const data = await aiResponse.json();
    const content = data.choices?.[0]?.message?.content;
    
    if (!content) {
      return null;
    }

    // Parse JSON from response
    try {
      // Extract JSON from markdown code block if present
      const jsonMatch = content.match(/```json\n?([\s\S]*?)\n?```/) || 
                        content.match(/```\n?([\s\S]*?)\n?```/) ||
                        [null, content];
      
      const jsonStr = jsonMatch[1] || content;
      const parsed: AIResponse = JSON.parse(jsonStr.trim());
      
      return {
        cheapestDrink: parsed.drink || null,
        cheapestFood: parsed.food || null,
      };
    } catch (parseError) {
      console.error('Failed to parse AI response:', parseError);
      return null;
    }
  } catch (error) {
    console.error('Error parsing menu:', error);
    return null;
  }
}

/**
 * Update CSV with cheapest items for a restaurant
 */
export async function updateCheapestItems(
  place: HappyHourPlace,
  apiKey: string
): Promise<void> {
  if (!place.website_url) {
    return;
  }

  // Try common menu URLs
  const menuUrls = [
    `${place.website_url}/menu`,
    `${place.website_url}/happy-hour`,
    `${place.website_url}/specials`,
    `${place.website_url}/drinks`,
    place.website_url,
  ];

  for (const url of menuUrls) {
    const items = await parseMenuWithAI(place.restaurant_name, url, apiKey);
    
    if (items?.cheapestDrink || items?.cheapestFood) {
      // TODO: Update CSV with items
      console.log(`Found items for ${place.restaurant_name}:`, items);
      return;
    }
  }
}
