import { describe, it, expect, vi } from 'vitest';
import { extractCheapestItems, parseMenuWithAI } from '../src/lib/menu-parser';

describe('extractCheapestItems', () => {
  it('finds cheapest drink from menu items', () => {
    const menuItems = [
      { name: 'IPA Beer', price: 7.00, category: 'drink' },
      { name: 'Lager', price: 5.00, category: 'drink' },
      { name: 'Stout', price: 6.50, category: 'drink' },
      { name: 'Burger', price: 12.00, category: 'food' },
    ];
    
    const cheapest = extractCheapestItems(menuItems);
    
    expect(cheapest.cheapestDrink).toEqual({ name: 'Lager', price: 5.00 });
  });

  it('finds cheapest food from menu items', () => {
    const menuItems = [
      { name: 'Burger', price: 12.00, category: 'food' },
      { name: 'Tacos', price: 8.00, category: 'food' },
      { name: 'Fries', price: 5.00, category: 'food' },
      { name: 'IPA', price: 7.00, category: 'drink' },
    ];
    
    const cheapest = extractCheapestItems(menuItems);
    
    expect(cheapest.cheapestFood).toEqual({ name: 'Fries', price: 5.00 });
  });

  it('handles items without prices', () => {
    const menuItems = [
      { name: 'Market Price Fish', price: null, category: 'food' },
      { name: 'Fries', price: 5.00, category: 'food' },
    ];
    
    const cheapest = extractCheapestItems(menuItems);
    
    expect(cheapest.cheapestFood).toEqual({ name: 'Fries', price: 5.00 });
  });

  it('handles empty menu', () => {
    const cheapest = extractCheapestItems([]);
    
    expect(cheapest.cheapestDrink).toBeNull();
    expect(cheapest.cheapestFood).toBeNull();
  });

  it('handles menu with only drinks', () => {
    const menuItems = [
      { name: 'IPA', price: 7.00, category: 'drink' },
    ];
    
    const cheapest = extractCheapestItems(menuItems);
    
    expect(cheapest.cheapestDrink).toEqual({ name: 'IPA', price: 7.00 });
    expect(cheapest.cheapestFood).toBeNull();
  });
});

describe.skip('parseMenuWithAI - integration test', () => {
  it('should parse AI response with menu items', async () => {
    // Requires API key and network access
    const result = await parseMenuWithAI('Kairoa Brewing', 'https://example.com/menu', 'test-key');
    expect(result).toBeDefined();
  });
});
