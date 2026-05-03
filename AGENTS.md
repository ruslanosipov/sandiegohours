<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Happy Hour Finder - Developer Guide

## Project Overview
Next.js website displaying happy hours for restaurants/bars near 92116 (Normal Heights/North Park, San Diego).

## Tech Stack
- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS
- **Testing**: Vitest (TypeScript), pytest (Python)
- **Data**: CSV files (happy_hours.csv, menu_data.csv)
- **APIs**: Google Places API (New) v1 for restaurant data + happy hours
- **AI**: OpenRouter for website parsing

## Architecture

### Data Flow
```
Google Places API → Python Pipeline → CSV Storage → Next.js Frontend
                        ↓
               AI Website Parsing (OpenRouter)
```

### Python Pipeline
```
scripts/orchestrator.py
  ├── fetchers/google_places.py           # Google Places API v1 (sync)
  ├── fetchers/google_places_async.py     # Parallel Place Details (async)
  ├── fetchers/website.py                 # Website scraping with caching
  ├── fetchers/website_fetcher.py         # (legacy alias)
  ├── processors/happy_hours.py           # AI happy hour extraction (sync)
  ├── processors/happy_hours_async.py    # Parallel AI extraction (async)
  ├── processors/menus.py                 # AI menu/deals extraction (sync)
  ├── processors/menus_async.py           # Parallel AI extraction (async)
  ├── storage/csv_manager.py              # CSV read/write
  └── ai/openrouter.py                    # OpenRouter client (sync + async)
```

#### Async Parallelization
The pipeline now runs **fully async** via `httpx`:
- **Google Places Place Details**: Up to **10 concurrent** requests (cap under ~600/min default quota).
- **OpenRouter AI parsing**: Up to **50 concurrent** requests (well within high-tier limits).
- **Website priority-path checks**: Every restaurant's `/happy-hour`, `/specials`, etc. are probed in parallel using `asyncio.gather`.

Tunables at the top of `scripts/orchestrator.py`:
```python
GOOGLE_PLACES_CONCURRENCY = 10
OPENROUTER_CONCURRENCY = 50
WEBSITE_FETCH_DELAY = 0.0   # optional delay between site fetches
```

All original sync APIs remain untouched for backward compatibility and testing.

### Frontend
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

## CSV Schema

### happy_hours.csv
```
restaurant_name,address,phone_number,website_url,happy_hour_times,regular_hours,
rating,review_count,price_level,source,freshness_date,latitude,longitude,
google_maps_url,generative_summary,cheapest_drink,cheapest_drink_price,
cheapest_food,cheapest_food_price,menu_summary
```

Key fields:
- `google_maps_url`: Direct link to Google Maps place
- `generative_summary`: One-sentence editorial summary from Places API
- `happy_hour_times`: Pipe-delimited list (e.g., "Monday: 3:00 PM - 6:00 PM | Tuesday: ...")
- `source`: Indicates data origin (e.g., "Google Places API (Happy Hours)", "Website (AI parsed)")

## Running the Project

```bash
# Install dependencies
npm install

# Run tests
npx vitest run              # TypeScript tests
python -m pytest tests/     # Python tests

# Development
npm run dev                 # http://localhost:3000

# Production build
npm run build               # Static export to dist/
npm run start               # Serve production build
```

## Data Pipeline

### Running the Pipeline
```bash
# Full refresh (fetches all data from Google Places API)
python scripts/orchestrator.py --full

# Resume from last step (uses cached data)
python scripts/orchestrator.py
```

### Pipeline Steps
1. **fetch** - Get restaurants from Google Places API
2. **parse_happy_hours** - AI website scraping for happy hours
3. **overrides** - Apply manual corrections from `public/manual_overrides.csv`
4. **parse_menus** - AI menu analysis
5. **summary** - Generate report

### Fetch Details
- Uses Google Places API (New) v1 text search with pagination
- Searches multiple keywords: "restaurant", "bar", "happy hour", "pub", "grill", "kitchen"
- Gets up to 60 results per keyword (3 pages × 20 results via nextPageToken)
- Deduplicates results across keywords
- Fetches details including: name, address, phone, website, hours, happy hours, rating, reviews, price level, coordinates

### Important Notes
- Pipeline saves progress to `.cache/progress.json`
- If interrupted, re-run to resume from last completed step
- Happy hour parsing is slow (AI calls take time)

## Testing

### Python Tests
- Use pytest
- Run: `python -m pytest tests/ -v`
- Key test files:
  - `tests/test_google_maps_fields.py` - Google Maps integration
  - `tests/test_fetchers.py` - Website fetching
  - `tests/test_orchestrator_storage.py` - CSV read/write

### TypeScript Tests
- Use Vitest
- Run: `npx vitest run`
- Test files in `tests/*.test.ts`

## Code Patterns

### Adding New Fields

1. **Backend (Python)**:
   - Add field to `scripts/storage/models.py` (Restaurant dataclass)
   - Update `scripts/fetchers/google_places.py` field mask and conversion
   - Add tests in `tests/test_<feature>.py`

2. **Frontend (TypeScript)**:
   - Add field to `src/types/happy-hour.ts` (HappyHourPlace interface)
   - Update `src/app/components/HappyHourFinder.tsx` to display
   - Update `tests/google-places-conversion.test.ts`

3. **Regenerate Data**:
   - Run `python scripts/orchestrator.py --full`
   - Run `npm run build` to update static site

## Common Issues

### Node Build Process Already Running
If you try to run `npx next build` while a build/dev server is already running, you may see:
```
Another next build process is already running.
```

**Solution**: Wait for the build to complete — do NOT try to kill `node.exe` processes. If the build is truly stuck (not just slow), check `.next/build.lock` and delete it only if you're confident the process is dead. Then retry the build.

### Windows Console Unicode Encoding
The Google Places API returns Unicode characters (thin spaces `\u2009`, narrow non-breaking spaces `\u202f`) in time strings. These cause `UnicodeEncodeError` when printing to Windows console.

**Solution**: Wrap print statements in try/except:
```python
try:
    print(f"Processing: {restaurant_name}")
except UnicodeEncodeError:
    print("Processing: <Unicode content>")
```

### API Field Names
Google Places API (New) v1 uses different field names than legacy API:
- `editorialSummary` - One-sentence description (not `generativeSummary`)
- `googleMapsUri` - Maps URL
- `currentSecondaryOpeningHours` - Happy hour times
- `regularOpeningHours` - Regular business hours

### Data Refresh Strategy
- `--full` flag fetches fresh data from Google Places API
- Without `--full`, pipeline skips fetch step and uses existing CSV
- Happy hours are merged: API data + AI website parsing

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

## File Structure

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
│   ├── menu_data.csv           # Menu/parsing results
│   └── manual_overrides.csv    # Manual corrections
└── dist/                       # Built static site
```

## Known Issues
- Rating of 0 becomes empty string (falsy value bug in conversion)
- Some restaurants have coordinates but no happy hour data
- OpenRouter rate limits on free tier

## Future Ideas
- User-contributed happy hour updates
- Photos of happy hour deals
- "Add to Calendar" button
- Push notifications when happy hour starts nearby
