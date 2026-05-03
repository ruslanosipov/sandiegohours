import { describe, it, expect } from 'vitest';
import { MenuData, formatMenuCSV, parseMenuCSV, generateCheapestSummary } from '../src/lib/menu-csv';

describe('generateCheapestSummary', () => {
  it('creates concise summary from cheapest items', () => {
    const data: MenuData = {
      restaurant_name: 'Test Bar',
      cheapest_drink: '$5 bottled beer',
      cheapest_drink_price: 5,
      cheapest_food: '$1 wings',
      cheapest_food_price: 1,
      all_drink_options: ['$5 bottled', '$7 draft', '$9 cocktails'],
      all_food_options: ['$1 wings', '$3 sliders', '$6 nachos'],
    };
    
    const summary = generateCheapestSummary(data);
    expect(summary).toBe('$1 wings, $3 sliders, $5 bottled, $6 nachos, $7 draft and $9 cocktails');
  });

  it('handles only drinks', () => {
    const data: MenuData = {
      restaurant_name: 'Drink Only',
      cheapest_drink: '$4 wells',
      cheapest_drink_price: 4,
      cheapest_food: '',
      cheapest_food_price: null,
      all_drink_options: ['$4 wells', '$6 wine'],
      all_food_options: [],
    };
    
    const summary = generateCheapestSummary(data);
    expect(summary).toBe('$4 wells and $6 wine');
  });

  it('handles empty options', () => {
    const data: MenuData = {
      restaurant_name: 'Empty',
      cheapest_drink: '',
      cheapest_drink_price: null,
      cheapest_food: '',
      cheapest_food_price: null,
      all_drink_options: [],
      all_food_options: [],
    };
    
    const summary = generateCheapestSummary(data);
    expect(summary).toBe('');
  });
});

describe('formatMenuCSV', () => {
  it('formats menu data as CSV row', () => {
    const data: MenuData = {
      restaurant_name: 'The Hangout',
      cheapest_drink: '$5 bottled beer',
      cheapest_drink_price: 5,
      cheapest_food: '$1 wings',
      cheapest_food_price: 1,
      all_drink_options: ['$5 bottled', '$7 draft', '$9 cocktails'],
      all_food_options: ['$1 wings', '$3 sliders', '$6 nachos'],
    };
    
    const csv = formatMenuCSV(data);
    expect(csv).toContain('The Hangout');
    expect(csv).toContain('$5 bottled beer');
    expect(csv).toContain('$1 wings');
    expect(csv).toContain('The Hangout');
    expect(csv).toContain('$5 bottled beer');
    expect(csv).toContain('$1 wings');
  });
});

describe('parseMenuCSV', () => {
  it('parses CSV row back to MenuData', () => {
    const csvLine = 'The Hangout,$5 bottled beer,5,$1 wings,1,$1 wings, $3 sliders, $5 bottled,$7 draft, $8 cocktails';
    
    const parsed = parseMenuCSV(csvLine);
    expect(parsed.restaurant_name).toBe('The Hangout');
    expect(parsed.cheapest_drink).toBe('$5 bottled beer');
    expect(parsed.cheapest_drink_price).toBe(5);
    expect(parsed.cheapest_food).toBe('$1 wings');
    expect(parsed.cheapest_food_price).toBe(1);
  });

  it('parses place_id-prefixed CSV row', () => {
    const csvLine = 'ChIJabc123,The Hangout,$5 bottled beer,5,$1 wings,1,summary here';
    const parsed = parseMenuCSV(csvLine);
    expect(parsed.place_id).toBe('ChIJabc123');
    expect(parsed.restaurant_name).toBe('The Hangout');
    expect(parsed.cheapest_drink).toBe('$5 bottled beer');
    expect(parsed.cheapest_drink_price).toBe(5);
  });
});
