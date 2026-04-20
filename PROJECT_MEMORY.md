# Happy Hour Finder - Project Memory

## Project Overview
Next.js website displaying happy hours for restaurants/bars near 92116 (Normal Heights/North Park, San Diego).

## Tech Stack
- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS
- **Testing**: Vitest (TypeScript), pytest (Python)
- **Data**: CSV with lat/lng coordinates
- **APIs**: Google Maps Places API (for coordinates)

## Key Features
- Distance-based sorting with geolocation
- Time-accurate happy hour status (Active/Later/Passed/No HH Today/No HH)
- Search by name/address
- Day/time filtering
- Responsive grid layout

## Running the Project

```bash
# Install dependencies
npm install

# Run tests (TDD - do this first!)
npx vitest run          # TypeScript tests
python -m pytest tests/ # Python tests

# Build static site
npm run build           # Outputs to dist/

# Test build locally
npx serve dist
```

## TDD Workflow
1. Write test first (describe expected behavior)
2. Run test - watch it fail
3. Implement minimal code to pass
4. Run test - confirm it passes
5. Refactor if needed
6. Commit with descriptive message

## Project Structure
```
happy-hour-finder/
├── src/
│   ├── app/components/HappyHourFinder.tsx  # Main UI
│   ├── lib/happy-hour-utils.ts             # Time parsing & status logic
│   ├── lib/distance-utils.ts               # Haversine formula
│   └── hooks/useUserLocation.ts            # Geolocation hook
├── tests/                                   # Vitest tests
├── public/happy_hours.csv                   # Data with lat/lng
└── dist/                                    # Built static site
```

## Key Learnings

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

## Testing Strategy
- **Unit tests**: Time parsing, status logic, distance calc
- **Component tests**: HappyHourFinder rendering, interactions
- **Test coverage**: 104+ TypeScript tests, 43 Python tests

## Known Issues (Skipped)
- Unicode special character edge cases (low priority)
- Hook tests need React Testing Library setup fixes

## Future Ideas
- Add "Add to Calendar" button
- Show happy hour menu items if available
- User-contributed happy hour updates
- Photos of happy hour deals
