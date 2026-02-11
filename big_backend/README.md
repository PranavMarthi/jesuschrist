# prelimtesting_polyworld

Backend-only project with:

- `backend/` FastAPI endpoint to query geocoded Polymarket questions by place

## Backend

From `backend`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Optional environment overrides for data source:

- `POLYWORLD_RESULTS_FILE` (defaults to `../polymarket_all_results.json`)
- `POLYWORLD_CACHE_FILE` (defaults to `../.geolocate_cache.json`)
- `GOOGLE_MAPS_API_KEY` (optional; enables Google Maps place resolution for specific place queries like "Madison Square Garden")

Endpoints:

- `GET /health`
- `GET /markets?query=washington`
- `GET /api/v1/events/by-location?location=washington%20dc&strict=true&limit=100&offset=0`
