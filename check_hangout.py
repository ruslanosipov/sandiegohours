from scripts.fetchers.google_places import search_places_text

# Search specifically for The Hangout
places, token = search_places_text('32.762889,-117.119922', radius=800, keyword='The Hangout Normal Heights')
print(f'Found {len(places)} places')
for p in places:
    name = p.get('displayName', {}).get('text', 'Unknown')
    loc = p.get('location', {})
    if loc:
        print(f"  {name}: {loc.get('latitude')}, {loc.get('longitude')}")
    else:
        print(f"  {name}: No location")

# Also check with broader search
print("\nSearching 'restaurant'...")
places2, token2 = search_places_text('32.762889,-117.119922', radius=800, keyword='restaurant')
for p in places2:
    name = p.get('displayName', {}).get('text', 'Unknown')
    if 'hangout' in name.lower():
        print(f"  FOUND: {name}")
