# Happy Hour Finder - Project Memory

## Project Overview
Next.js website displaying happy hours for restaurants/bars near 92116 (Normal Heights/North Park, San Diego).

## Tech Stack
- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS
- **Testing**: Vitest (TypeScript), pytest (Python)
- **Data**: CSV files (happy_hours.csv, menu_data.csv)
- **APIs**: Google Places API (New) v1 for restaurant data + happy hours
- **AI**: OpenRouter for website parsing

## Architecture

### Data Pipeline (Python)
```
orchestrator.py
  ├── fetchers/google_places.py    # Google Places API v1 with pagination
  ├── fetchers/website_fetcher.py  # Website scraping with caching
  ├── processors/happy_hour.py     # AI happy hour extraction
  ├── processors/menu.py           # AI menu/deals extraction
  ├── storage/csv_manager.py       # CSV read/write
  └── ai/openrouter.py             # OpenRouter API client
```

### Frontend (Next.js)
```
src/
  ├── app/
  │   ├── page.tsx                  # Main page (server component)
  │   └── components/
  │       └── HappyHourFinder.tsx   # Main UI component
  ├── lib/
  │   ├── happy-hour-utils.ts       # Time parsing & status logic
  │   ├── distance-utils.ts         # Haversine formula & sorting
  │   └── menu-parser.ts            # Menu summary extraction
  └── types/
      └── happy-hour.ts             # TypeScript interfaces
```

## Key Features
- **Distance-based sorting** with geolocation
- **Time-accurate happy hour status** (Active/Later/Passed/No HH Today/No HH)
- **Search** by name/address
- **Day/time filtering** with visual indicators
- **Responsive grid layout**
- **Happy hour deals display** (cheapest drink/food from menu parsing)
- **Multi-source data**: Google Places API + website scraping + manual overrides

## Running the Project

```bash
# Install dependencies
npm install

# Run tests
npx vitest run              # TypeScript tests (153 tests)
python -m pytest tests/     # Python tests

# Development
npm run dev                 # http://localhost:3000

# Production build
npm run build               # Static export to dist/
npm run start               # Serve production build
```

## Data Pipeline

### 1. Fetch Restaurants
```bash
python scripts/orchestrator.py --full
```
- Uses Google Places API (New) v1 text search with pagination
- Searches multiple keywords: "restaurant", "bar", "happy hour", "pub", "grill", "kitchen"
- Gets up to 60 results per keyword (3 pages × 20 results via nextPageToken)
- Deduplicates results across keywords
- Fetches details including: name, address, phone, website, hours, happy hours, rating, reviews, price level, coordinates

### 2. Parse Happy Hours
- For restaurants without happy hour data from Google API
- Scrapes website using AI (OpenRouter)
- Extracts structured happy hour times

### 3. Parse Menus
- Scrapes happy hour menu pages
- Extracts cheapest drink and food items with prices
- Generates concise summary (e.g., "$1 wings, $5 bottled")

### 4. Apply Manual Overrides
- Reads manual_overrides.csv
- Overrides AI/API data with human-verified happy hours

## Testing Strategy
- **Unit tests**: Time parsing, status logic, distance calc, data conversion
- **Component tests**: HappyHourFinder rendering, interactions, missing data
- **Integration tests**: CSV parsing, menu extraction
- **Total**: 153 TypeScript tests, Python tests

## Project Structure
```
happy-hour-finder/
├── scripts/                    # Python data pipeline
│   ├── orchestrator.py         # Main pipeline entry point
│   ├── fetchers/               # API fetchers
│   ├── processors/             # AI processors
│   ├── storage/                # CSV management
│   └── ai/                     # OpenRouter client
├── src/                        # Next.js frontend
│   ├── app/
│   ├── lib/
│   └── types/
├── tests/                      # Vitest tests
├── public/
│   ├── happy_hours.csv         # Main restaurant data
│   └── menu_data.csv           # Menu/parsing results
└── dist/                       # Built static site
```

## Key Learnings

### Google Places API v1
- **Text Search** (searchText) supports pagination via nextPageToken
- **Nearby Search** (searchNearby) does NOT support pagination - max 20 results
- Use text search with multiple keywords to get comprehensive coverage
- Field masks required: `places.id,places.displayName,nextPageToken`

### Time Parsing Complexity
- Times come in many formats: "3pm", "3:00 pm", "3:00 PM", "15:00", "3 - 6 PM"
- Special chars: narrow non-breaking space (\u202f), en-dash (\u2013)
- Solution: normalize before parsing, inherit AM/PM from end time

### Status Logic
- Must check if current time is actually within happy hour range
- Handle "Closed" days different from missing days
- Case-insensitive day matching (Sunday, SUNDAY, sunday)

### Distance Calculation
- Use Haversine formula for accurate miles
- Show feet for <0.1mi, decimal miles otherwise
- Sort by distance when user location available

## Known Issues
- Rating of 0 becomes empty string (falsy value bug in conversion)
- Some restaurants have coordinates but no happy hour data
- OpenRouter rate limits on free tier

## Future Ideas
- User-contributed happy hour updates
- Photos of happy hour deals
- "Add to Calendar" button
- Push notifications when happy hour starts nearby
