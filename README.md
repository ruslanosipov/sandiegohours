# San Diego Happy Hour Finder

Find the best happy hours in Normal Heights, North Park & surrounding San Diego neighborhoods.

## Features

- 🍺 **271+ restaurants and bars** in the 92116 area
- 📍 **Distance-based sorting** using your location
- ⏰ **Real-time happy hour status** - see what's active right now
- 🔍 **Search** by restaurant name or address
- 📅 **Filter by day and time** to plan ahead
- 💰 **Happy hour deals** - cheapest drinks and food items

## Tech Stack

- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS
- **Data**: Google Places API (New) v1 + AI-powered website parsing
- **Testing**: Vitest (153 tests)

## Development

```bash
# Install dependencies
npm install

# Run tests
npx vitest run

# Start development server
npm run dev

# Build for production
npm run build
```

## Data Pipeline

The project includes a Python-based data pipeline that:

1. **Fetches restaurants** from Google Places API with pagination (gets 100+ results)
2. **Extracts happy hours** from Google API or scrapes websites with AI
3. **Parses menus** to find cheapest drink/food deals
4. **Applies manual overrides** for human-verified data

Run the pipeline:
```bash
python scripts/orchestrator.py --full
```

## Project Structure

```
├── scripts/          # Python data pipeline
│   ├── orchestrator.py
│   ├── fetchers/
│   ├── processors/
│   └── storage/
├── src/              # Next.js frontend
│   ├── app/
│   ├── lib/
│   └── types/
├── tests/            # Vitest tests
└── public/           # CSV data files
```

## License

MIT
