"""FastAPI endpoint for querying geocoded Polymarket questions by place."""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


ALIAS_MAP: dict[str, list[str]] = {
    "nyc": ["new york", "new york city"],
    "new york city": ["new york", "nyc"],
    "new york": ["nyc"],
    "dc": ["washington dc", "washington"],
    "washington dc": ["dc", "washington"],
    "la": ["los angeles"],
    "sf": ["san francisco"],
    "uk": ["united kingdom"],
    "uae": ["united arab emirates"],
    "us": ["united states", "usa"],
    "united states": ["us", "usa", "america"],
    "usa": ["united states", "us"],
    "america": ["united states", "usa", "us"],
}

logger = logging.getLogger("polyworld.api")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def parse_bool_env(value: str | None, default: bool = False) -> bool:
    """Parse common boolean environment variable values."""
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def parse_cors_origins(value: str | None) -> list[str]:
    """Parse comma-separated CORS origins with local-safe defaults."""
    if value is None or not value.strip():
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def normalize_text(value: str) -> str:
    """Normalize text for exact token matching."""
    cleaned = value.strip().lower()
    cleaned = cleaned.replace("&", " and ")
    cleaned = cleaned.replace(",", " ")
    cleaned = cleaned.replace(".", " ")
    cleaned = cleaned.replace("-", " ")
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\bd\s+c\b", "dc", cleaned)
    cleaned = re.sub(r"\bu\s+s\s+a\b", "usa", cleaned)
    cleaned = re.sub(r"\bu\s+s\b", "us", cleaned)
    cleaned = re.sub(r"\bu\s+k\b", "uk", cleaned)
    cleaned = re.sub(r"\bu\s+a\s+e\b", "uae", cleaned)
    return cleaned.strip()


def split_location_parts(location_name: str) -> list[str]:
    """Split a location string into comma-separated parts."""
    return [part.strip() for part in location_name.split(",") if part.strip()]


def build_tokens_from_location(location_name: str) -> set[str]:
    """Build exact-match tokens from a location string."""
    parts = [normalize_text(part) for part in split_location_parts(location_name)]
    parts = [part for part in parts if part]
    if not parts:
        return set()

    tokens: set[str] = set(parts)
    tokens.add(normalize_text(location_name))

    # Add cumulative suffixes to catch city/state and city/country exact queries.
    # Example: "Building, Washington, DC" -> "washington dc"
    for index in range(1, len(parts)):
        suffix = " ".join(parts[index:]).strip()
        if suffix:
            tokens.add(suffix)

    # Add adjacent pair combinations for compact queries.
    for index in range(len(parts) - 1):
        pair = f"{parts[index]} {parts[index + 1]}".strip()
        if pair:
            tokens.add(pair)

    for token in list(tokens):
        for alias in ALIAS_MAP.get(token, []):
            tokens.add(alias)

    return {token for token in tokens if token}


def parse_locations(record: dict[str, Any]) -> list[str]:
    """Extract all location_name strings from primary + locations array."""
    names: list[str] = []

    primary = record.get("location_name")
    if isinstance(primary, str) and primary.strip():
        names.append(primary.strip())

    locations = record.get("locations")
    if isinstance(locations, list):
        for item in locations:
            if isinstance(item, dict):
                name = item.get("location_name")
                if isinstance(name, str) and name.strip():
                    names.append(name.strip())

    return list(dict.fromkeys(names))


@dataclass(slots=True)
class MatchRef:
    """Reference to a matched record and why it matched."""

    index: int
    matched_location: str


@dataclass(slots=True)
class ResolvedPlace:
    """Google Maps resolution metadata for a free-text place query."""

    formatted_address: str
    latitude: float
    longitude: float
    candidates: list[str]


class MarketIndex:
    """In-memory search index over geocoded market records."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self.records = records
        self.token_index: dict[str, list[MatchRef]] = defaultdict(list)
        self._build()

    def _build(self) -> None:
        """Build token -> record references index."""
        for idx, record in enumerate(self.records):
            for location_name in parse_locations(record):
                tokens = build_tokens_from_location(location_name)
                for token in tokens:
                    self.token_index[token].append(MatchRef(index=idx, matched_location=location_name))

    def search(self, query: str) -> list[dict[str, Any]]:
        """Return unique records that exactly match normalized query tokens."""
        normalized_query = normalize_text(query)
        if not normalized_query:
            return []

        refs = self.token_index.get(normalized_query, [])
        if not refs:
            return []

        by_question: dict[str, dict[str, Any]] = {}
        for ref in refs:
            record = self.records[ref.index]
            question = str(record.get("question", "")).strip()
            if not question:
                continue

            existing = by_question.get(question)
            if existing is None:
                payload = dict(record)
                payload["matched_on"] = [ref.matched_location]
                by_question[question] = payload
            else:
                matched_on = existing.get("matched_on")
                if not isinstance(matched_on, list):
                    matched_on = []
                if ref.matched_location not in matched_on:
                    matched_on.append(ref.matched_location)
                existing["matched_on"] = matched_on

        return sorted(by_question.values(), key=lambda row: str(row.get("question", "")))


def build_query_variants(query: str) -> list[str]:
    """Build exact variants for place matching."""
    normalized = normalize_text(query)
    if not normalized:
        return []

    variants: set[str] = {normalized}
    parts = [part for part in normalized.split(" ") if part]

    if len(parts) >= 2:
        variants.add(" ".join(parts))

    for part in parts:
        if len(part) >= 2:
            variants.add(part)

    for token in list(variants):
        for alias in ALIAS_MAP.get(token, []):
            variants.add(alias)

    return sorted({variant for variant in variants if variant})


def build_exact_query_variants(query: str) -> list[str]:
    """Build conservative exact variants for strict location queries."""
    normalized = normalize_text(query)
    if not normalized:
        return []

    variants: set[str] = {normalized}
    for alias in ALIAS_MAP.get(normalized, []):
        variants.add(alias)

    return sorted({variant for variant in variants if variant})


def paginate_rows(rows: list[dict[str, Any]], offset: int, limit: int) -> tuple[list[dict[str, Any]], bool]:
    """Return paginated rows and has_more indicator."""
    sliced = rows[offset : offset + limit]
    has_more = offset + limit < len(rows)
    return sliced, has_more


def merge_result_groups(groups: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Merge result sets by question and combine matched_on values."""
    by_question: dict[str, dict[str, Any]] = {}
    for group in groups:
        for row in group:
            question = str(row.get("question", "")).strip()
            if not question:
                continue

            existing = by_question.get(question)
            if existing is None:
                by_question[question] = dict(row)
                continue

            existing_matched = existing.get("matched_on")
            row_matched = row.get("matched_on")
            existing_list = existing_matched if isinstance(existing_matched, list) else []
            row_list = row_matched if isinstance(row_matched, list) else []
            merged = list(dict.fromkeys([*existing_list, *row_list]))
            existing["matched_on"] = merged

    return sorted(by_question.values(), key=lambda row: str(row.get("question", "")))


def fetch_json(url: str, timeout_seconds: float = 5.0) -> dict[str, Any]:
    """Fetch JSON payload from URL using stdlib HTTP client."""
    with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
        raw = response.read().decode("utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        return {}
    return payload


def resolve_place_with_google(query: str, api_key: str) -> ResolvedPlace | None:
    """Resolve free-text place via Google Geocoding API and return search candidates."""
    params = urllib.parse.urlencode({"address": query, "key": api_key})
    url = f"https://maps.googleapis.com/maps/api/geocode/json?{params}"

    try:
        payload = fetch_json(url)
    except Exception:  # noqa: BLE001
        return None

    status = payload.get("status")
    results = payload.get("results")
    if status != "OK" or not isinstance(results, list) or not results:
        return None

    first = results[0]
    if not isinstance(first, dict):
        return None

    formatted_address = first.get("formatted_address")
    geometry = first.get("geometry")
    location = geometry.get("location") if isinstance(geometry, dict) else None
    if not isinstance(formatted_address, str) or not isinstance(location, dict):
        return None

    lat = location.get("lat")
    lng = location.get("lng")
    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        return None

    candidates = set(build_tokens_from_location(formatted_address))
    candidates.update(build_query_variants(query))

    components = first.get("address_components")
    if isinstance(components, list):
        by_type: dict[str, str] = {}
        by_type_short: dict[str, str] = {}

        for component in components:
            if not isinstance(component, dict):
                continue
            long_name = component.get("long_name")
            short_name = component.get("short_name")
            types = component.get("types")
            if not isinstance(types, list):
                continue

            if isinstance(long_name, str):
                candidates.add(normalize_text(long_name))
            if isinstance(short_name, str):
                candidates.add(normalize_text(short_name))

            for component_type in types:
                if isinstance(component_type, str):
                    if isinstance(long_name, str) and component_type not in by_type:
                        by_type[component_type] = long_name
                    if isinstance(short_name, str) and component_type not in by_type_short:
                        by_type_short[component_type] = short_name

        locality = by_type.get("locality")
        admin1 = by_type.get("administrative_area_level_1")
        admin1_short = by_type_short.get("administrative_area_level_1")
        country = by_type.get("country")
        country_short = by_type_short.get("country")

        combinations = [
            locality,
            admin1,
            admin1_short,
            country,
            country_short,
            f"{locality} {admin1_short}" if locality and admin1_short else None,
            f"{locality} {admin1}" if locality and admin1 else None,
            f"{locality} {country}" if locality and country else None,
            f"{admin1} {country}" if admin1 and country else None,
        ]
        for candidate in combinations:
            if isinstance(candidate, str) and candidate.strip():
                candidates.add(normalize_text(candidate))

    # Expand aliases once more from resolved candidates.
    for token in list(candidates):
        for alias in ALIAS_MAP.get(token, []):
            candidates.add(alias)

    normalized_candidates = sorted({token for token in candidates if token})
    return ResolvedPlace(
        formatted_address=formatted_address,
        latitude=round(float(lat), 6),
        longitude=round(float(lng), 6),
        candidates=normalized_candidates,
    )


def read_json(path: Path) -> Any:
    """Read JSON from disk."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_records(data_path: Path, cache_path: Path) -> tuple[list[dict[str, Any]], str]:
    """Load records from results/cache and merge cache into incomplete rows."""
    records_by_question: dict[str, dict[str, Any]] = {}
    source_parts: list[str] = []

    if data_path.exists():
        payload = read_json(data_path)
        if isinstance(payload, list):
            source_parts.append(str(data_path))
            for item in payload:
                if not isinstance(item, dict):
                    continue
                question = item.get("question")
                if not isinstance(question, str) or not question.strip():
                    continue
                records_by_question[question] = dict(item)

    if cache_path.exists():
        cache_payload = read_json(cache_path)
        if isinstance(cache_payload, dict):
            source_parts.append(str(cache_path))
            for question, row in cache_payload.items():
                if not isinstance(question, str) or not isinstance(row, dict):
                    continue

                cache_record = dict(row)
                cache_record["question"] = question
                cache_record["source"] = "cache"

                existing = records_by_question.get(question)
                if existing is None:
                    records_by_question[question] = cache_record
                    continue

                existing_location = existing.get("location_name")
                existing_locations = existing.get("locations")
                existing_has_error = "error" in existing and bool(existing.get("error"))
                existing_incomplete = (
                    not isinstance(existing_location, str)
                    and not (isinstance(existing_locations, list) and len(existing_locations) > 0)
                )

                if existing_has_error or existing_incomplete:
                    merged = dict(existing)
                    for key in (
                        "entity",
                        "reasoning",
                        "location_name",
                        "latitude",
                        "longitude",
                        "locations",
                        "category",
                    ):
                        if key in cache_record:
                            merged[key] = cache_record[key]
                    merged["source"] = "cache"
                    merged.pop("error", None)
                    records_by_question[question] = merged

    records = list(records_by_question.values())
    if not records:
        raise FileNotFoundError(
            "No data source found. Expected polymarket_all_results.json or .geolocate_cache.json"
        )

    return records, " + ".join(source_parts) if source_parts else "unknown"


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(title="Polyworld Markets API", version="0.1.0")

    allow_origins = parse_cors_origins(os.getenv("POLYWORLD_CORS_ORIGINS"))
    allow_credentials = parse_bool_env(os.getenv("POLYWORLD_CORS_ALLOW_CREDENTIALS"), default=False)

    if "*" in allow_origins and allow_credentials:
        allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )

    project_root = Path(__file__).resolve().parent.parent
    data_path = Path(os.getenv("POLYWORLD_RESULTS_FILE", project_root / "polymarket_all_results.json"))
    cache_path = Path(os.getenv("POLYWORLD_CACHE_FILE", project_root / ".geolocate_cache.json"))

    records, source_file = load_records(data_path, cache_path)
    index = MarketIndex(records)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "records": len(records),
            "indexed_tokens": len(index.token_index),
            "data_source": source_file,
        }

    @app.get("/markets")
    def markets(
        query: str = Query(..., min_length=1, max_length=200, description="City, state, or country exact match")
    ) -> dict[str, Any]:
        q = query.strip()
        if not q:
            raise HTTPException(status_code=400, detail="query is required")

        variants = build_query_variants(q)
        groups = [index.search(variant) for variant in variants]

        maps_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
        resolved_place: ResolvedPlace | None = None
        if maps_key:
            resolved_place = resolve_place_with_google(q, maps_key)
            if resolved_place is not None:
                google_groups = [index.search(variant) for variant in resolved_place.candidates]
                groups.extend(google_groups)

        results = merge_result_groups(groups)
        return {
            "query": q,
            "count": len(results),
            "used_variants": variants,
            "resolved_place": {
                "formatted_address": resolved_place.formatted_address,
                "latitude": resolved_place.latitude,
                "longitude": resolved_place.longitude,
                "candidates": resolved_place.candidates,
            }
            if resolved_place is not None
            else None,
            "results": results,
        }

    @app.get("/api/v1/events/by-location")
    def events_by_location(
        location: str = Query(..., min_length=1, max_length=200, description="Location string (city/state/country/place)"),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        strict: bool = Query(True, description="If true, use exact matching only"),
    ) -> dict[str, Any]:
        raw = location.strip()
        if not raw:
            raise HTTPException(status_code=400, detail="location is required")

        exact_variants = build_exact_query_variants(raw)
        exact_groups = [index.search(variant) for variant in exact_variants]
        exact_results = merge_result_groups(exact_groups)

        mode = "exact"
        used_variants = exact_variants
        all_results = exact_results

        if not strict and not exact_results:
            fallback_variants = build_query_variants(raw)
            fallback_groups = [index.search(variant) for variant in fallback_variants]
            all_results = merge_result_groups(fallback_groups)
            used_variants = fallback_variants
            mode = "fallback"

        paged_results, has_more = paginate_rows(all_results, offset=offset, limit=limit)
        logger.info(
            "events lookup location=%s strict=%s mode=%s count=%s offset=%s limit=%s",
            raw,
            strict,
            mode,
            len(all_results),
            offset,
            limit,
        )
        for row in paged_results:
            question = str(row.get("question", "")).strip()
            if question:
                logger.info("matched event: %s", question)

        return {
            "location": raw,
            "normalized_location": normalize_text(raw),
            "mode": mode,
            "strict": strict,
            "used_variants": used_variants,
            "count": len(all_results),
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
            "results": paged_results,
        }

    return app


app = create_app()
