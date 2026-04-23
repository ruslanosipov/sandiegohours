<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Happy Hour Finder - Developer Guide

## Architecture Overview

This is a Next.js 16 + React 19 + TypeScript frontend with a Python data pipeline that fetches restaurant data from Google Places API.

### Data Flow
1. **Python Pipeline** (`scripts/orchestrator.py`) fetches data from Google Places API
2. **AI Parsing** extracts happy hours from restaurant websites using OpenRouter AI
3. **CSV Storage** - Data stored in `public/happy_hours.csv` and `public/menu_data.csv`
4. **Next.js Frontend** reads CSV files at build time and displays them

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

### Important Notes
- Pipeline saves progress to `.cache/progress.json`
- If interrupted, re-run to resume from last completed step
- Happy hour parsing is slow (AI calls take time)

## Common Issues

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

## File Structure

```
scripts/
  orchestrator.py          # Main data pipeline
  fetchers/
    google_places.py       # Places API integration
  storage/
    models.py              # Restaurant dataclass
    csv_manager.py         # CSV read/write

src/
  app/
    components/
      HappyHourFinder.tsx  # Main UI component
  types/
    happy-hour.ts          # TypeScript interfaces

public/
  happy_hours.csv          # Restaurant data
  menu_data.csv            # Menu item data
  manual_overrides.csv     # Manual corrections

tests/
  test_*.py                # Python tests
  *.test.ts                # TypeScript tests
```
