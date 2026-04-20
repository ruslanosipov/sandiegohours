#!/usr/bin/env python3
"""
Merge API data with manual overrides
Manual overrides take precedence
"""
import csv
from datetime import datetime

def load_manual_overrides():
    """Load manual override CSV"""
    overrides = {}
    try:
        with open('manual_overrides.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('restaurant_name', '').strip().lower()
                if name:
                    overrides[name] = {
                        'happy_hour_times': row.get('happy_hour_times', ''),
                        'source': row.get('source', 'Manual'),
                        'freshness_date': row.get('freshness_date', datetime.now().strftime('%Y-%m-%d'))
                    }
        print(f"Loaded {len(overrides)} manual overrides")
    except FileNotFoundError:
        print("No manual overrides file found")
    return overrides

def main():
    # Load manual overrides
    overrides = load_manual_overrides()
    
    # Read main data
    csv_path = 'public/happy_hours.csv'
    
    places = []
    applied = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            name = row.get('restaurant_name', '').strip().lower()
            
            # Apply override if exists
            if name in overrides:
                row['happy_hour_times'] = overrides[name]['happy_hour_times']
                row['source'] = overrides[name]['source']
                row['freshness_date'] = overrides[name]['freshness_date']
                applied.append(row.get('restaurant_name'))
            
            places.append(row)
    
    # Write back
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(places)
    
    print(f"\nApplied overrides to {len(applied)} places:")
    for name in applied:
        print(f"  - {name}")
    
    # Count
    with_hh = sum(1 for p in places if p.get('happy_hour_times', '').strip())
    print(f"\nTotal places: {len(places)}")
    print(f"With happy hour: {with_hh}")

if __name__ == "__main__":
    main()
