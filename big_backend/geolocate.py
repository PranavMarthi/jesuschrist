"""Geolocate prediction market questions to a single real-world location via OpenAI."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
from pathlib import Path
from typing import Any

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)


SYSTEM_PROMPT = """You are a geocoding engine for prediction market questions. Given a question, determine the most relevant real-world location and additional relevant locations whenever applicable, then return structured JSON. You must ALWAYS return valid JSON and nothing else - no markdown fences, no preamble, no commentary.

Mental model:
Every prediction market question is anchored through:
QUESTION -> PRIMARY ENTITY (or ENTITIES) -> PHYSICAL LOCATION(S) -> COORDINATES

Multi-location-first principle:
- Be liberal in returning multiple locations in `locations` whenever the question involves multiple entities, sides, institutions, teams, countries, people, or venues.
- Multi-location may be explicit (e.g., "A vs B", "X and Y", "between") OR implicit through an event/person chain.
- If an event spans multiple meaningful anchors (host venue + governing body + counterparties), include them when they materially add context.
- Keep `location_name`/`latitude`/`longitude` as the primary anchor, and use `locations` for the fuller set.

Resolution rules (ordered by priority, apply first matching rule):
0) strict_null_overrides
- For any crypto-related question, always set location_name/latitude/longitude to null and locations to an empty array.
- For globally scoped questions, always set location_name/latitude/longitude to null and locations to an empty array.

1) explicit_location
- If the question names a specific place/city/country/landmark, use that place directly.
- For bilateral action questions, use where the action physically happens.

2) sports_team
- Use the team's home venue (stadium/arena).
- For "Team A vs Team B", use first-listed team home venue.
- For matchups/rivalries/series, include both teams' home venues in `locations`.

3) sports_player_or_coach
- Individual awards/stat leaders: use player's or coach's current team home venue.
- Tournament-specific outcomes: use tournament venue.
- For awards and tournaments, include both the event venue and the primary team/person anchor in `locations` when they differ.

4) political_person_in_office
- Use the seat of power for their role (palace/residence/capitol/city hall).

5) political_candidate_or_nominee
- State/provincial elections: state capitol.
- National elections/party nominations: national seat of government or capital.
- Mayoral: city hall.

6) company_or_startup
- Use current headquarters.

7) crypto_token_or_protocol
- Use headquarters of company/foundation/core team behind token/protocol.
- Heuristics for major tokens: BTC->Miami, ETH->Zug (Ethereum Foundation), XRP->San Francisco (Ripple), SOL->San Francisco (Solana Labs).
- If unknown after best effort: default San Francisco, CA.
- Note: strict null override still applies for crypto questions in this tool.

8) institution_or_regulatory_body
- Use institution's primary seat/headquarters.

9) entertainment_awards_and_media
- Awards: ceremony venue.
- Specific events/festivals: event venue.
- General movie/music: Hollywood, Los Angeles, CA.
- Franchise question: production company HQ.
- For co-productions, collaborations, or multi-party franchises, include multiple relevant HQ/venues in `locations` when meaningful.

10) military_clash_between_nations
- Use likely geographic flashpoint/conflict zone.
- China-Taiwan: Taiwan Strait. China-Philippines: South China Sea.
- Israel-Iran: target country location.
- For bilateral clashes (e.g., "Israel x Turkey military clash"), include multiple relevant locations in `locations`.
- For each named sovereign country in the clash, include one anchor in `locations` using either:
  - the leader's governing seat/residence (presidential palace / prime minister office), preferred, or
  - the national capital if governing seat cannot be identified reliably.
- If a clear conflict flashpoint exists, include it as an additional location in `locations`, plus both countries' leader/government-seat anchors.
- Do not return only one side for bilateral clashes unless the question explicitly targets only one side.

11) trade_deal_or_bilateral_agreement
- U.S. trade deal: use the other country's capital.
- Otherwise use smaller/less prominent party's capital.
- For bilateral agreements, include both parties' governing anchors in `locations`.

12) natural_disaster_or_climate
- Location-specific disaster: likely impact zone.
- Global/unanchored health or climate: relevant global body HQ (e.g., Geneva for WHO/WMO).

13) technology_and_ai
- Specific AI/tech company: company HQ.
- General AI milestone: San Francisco, CA.

14) person_not_in_office
- Business figure: primary company HQ.
- Celebrity: most associated city.
- Former political figure: capital of jurisdiction served.

15) crypto_mindshare
- Use known residence/operating city of personality; if unknown San Francisco, CA.

16) legislative_policy
- Use legislature/regulatory body responsible for the action.
- For country-level policy questions, anchor to the leader's governing seat/residence first; if unavailable, use national capital.
- For state/province/city policy, use the relevant government headquarters building (state capitol/city hall).
- If the responsible institution and leader seat are different but both are materially relevant, include both in `locations`.

19) finance_default_hub
- For finance questions (rates, stocks, indices, macro policy, earnings, bankruptcy, debt), use the primary financial hub of the relevant jurisdiction/company market when no better institution building is specified.
- Prefer building-level institutions when explicit (e.g., central bank HQ, exchange building); otherwise use the financial district/hub city.
- Examples of hub behavior: U.S. -> New York (Wall Street), UK -> London (City of London), Japan -> Tokyo.

20) sports_default_venue
- For sports questions, default to the specific arena/stadium/track/course venue.
- Team-level questions: home arena/stadium.
- Matchups: first-listed team home venue unless a known neutral site is specified.
- Tournament/final/event questions: event venue.

17) miscellaneous_and_novelty
- Identify most substantive real-world anchor and follow chain.

18) no_clear_location
- If the question is fundamentally a pure price/market threshold (for example, "Will XRP reach $5.00?") and has no clear real-world location anchor, return null location fields.
- In this case, keep a valid entity/category/reasoning, but set:
  - "location_name": null
  - "latitude": null
  - "longitude": null

Categories (must be exactly one):
sports, politics, geopolitics, crypto, tech, finance, entertainment, science, natural_disaster, other

High-level defaults:
- military and policy -> leader/government-seat location for each relevant country/jurisdiction
- sports -> arena/stadium/venue
- finance -> financial hub city or district (unless explicit institution building is available)

Coordinate precision:
- Return latitude/longitude as decimal degrees with 4 decimal precision.
- Use specific building/venue/landmark coordinates when possible; otherwise relevant area center.

Output format (ONLY valid JSON object, no extra text):
{
  "entity": "Primary entity name and clarifying detail",
  "reasoning": "One concise sentence showing Entity -> Location chain",
  "location_name": "Specific place name, City, State/Country",
  "latitude": 0.0000,
  "longitude": 0.0000,
  "locations": [
    {
      "location_name": "Specific place name, City, State/Country",
      "latitude": 0.0000,
      "longitude": 0.0000
    }
  ],
  "category": "sports|politics|geopolitics|crypto|tech|finance|entertainment|science|natural_disaster|other"
}

Strict rules:
- entity must unambiguously identify anchor.
- reasoning must be exactly one sentence.
- latitude/longitude must be numeric when present (not strings).
- if there is no clear location anchor, set location_name/latitude/longitude to null.
- `locations` is optional, but when present it must be an array of location objects with location_name/latitude/longitude.
- for bilateral/multi-entity questions, include 2+ entries in `locations` whenever meaningful.
- for military/political clashes between two countries, `locations` should include at least one anchor per country.
- when in doubt between one vs many, prefer including `locations` with additional relevant anchors.
- `locations` must contain at most 3 entries (max 3). Keep the 3 most informative anchors.
- do not include original question.
- if confidence is very low and no reliable anchor exists, return null location_name/latitude/longitude and locations as an empty array.

Granularity requirements:
- Prefer building-level or venue-level locations over city-level whenever possible.
- Use the most specific known location available: arena/stadium/theater/courthouse/capitol/office tower/campus.
- Prefer official headquarters building or governing building over city center for institutions and companies.
- For politicians and officeholders, use the official governing/residence building for that role.
- For sports teams and events, use the exact home venue or event venue.
- Include specific address-level detail in location_name when reliably known (building name and street address), otherwise include building name with city/state/country.
- Never invent fake street addresses: if exact street address is uncertain, keep to verified building-level naming.
- Keep coordinates aligned to the specific building/venue entrance or centroid when possible.
- Never return only a bare country name (e.g., "Iran") when a capital, government-seat building, arena, headquarters, district, or flashpoint can be identified.
"""

REFINEMENT_PROMPT = """You are revising a previously too-generic geolocation result.

Given a prediction market question and a prior JSON answer, return a stricter, more specific JSON answer.

Rules:
- Keep category consistent with the question.
- Prefer building/venue-level specificity whenever possible.
- For military and policy questions, anchor to leader/government seat first, then national capital fallback.
- For sports, use arena/stadium/venue.
- For finance, use institution building when explicit, otherwise financial hub city/district.
- For bilateral geopolitical clashes, include flashpoint plus both countries' anchors in `locations` when identifiable.
- Do not use only a bare country name unless absolutely unavoidable.
- Keep `locations` to max 3 entries.
- If confidence is too low, return null location_name/latitude/longitude and empty `locations`.

Return valid JSON only with fields:
entity, reasoning, location_name, latitude, longitude, locations (optional), category
"""


REQUIRED_FIELDS: tuple[str, ...] = (
    "entity",
    "reasoning",
    "location_name",
    "latitude",
    "longitude",
    "category",
)

LOCATION_ENTRY_FIELDS: tuple[str, ...] = ("location_name", "latitude", "longitude")

CATEGORIES: set[str] = {
    "sports",
    "politics",
    "geopolitics",
    "crypto",
    "tech",
    "finance",
    "entertainment",
    "science",
    "natural_disaster",
    "other",
}


class ValidationError(Exception):
    """Raised when model JSON does not meet output schema."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(description="Geolocate prediction market questions")
    parser.add_argument("question", nargs="?", help="Single prediction market question")
    parser.add_argument(
        "--file",
        "-f",
        dest="file_path",
        help="Path to text file with one question per line",
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="output_path",
        default=None,
        help="Path to output JSON file (defaults to stdout)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="gpt-4.1-nano",
        help="OpenAI model (e.g. gpt-4.1-mini, gpt-4.1-nano)",
    )
    parser.add_argument(
        "--concurrency",
        "-c",
        type=int,
        default=20,
        help="Maximum concurrent API requests in batch mode (1-100)",
    )
    parser.add_argument(
        "--cache",
        default=".geolocate_cache.json",
        help='Cache file path, or "none" to disable',
    )
    parser.add_argument("--no-cache", action="store_true", help="Disable cache")
    parser.add_argument(
        "--retry",
        type=int,
        default=6,
        help="Maximum retries per question on failure",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run interactive mode (continuous questions from stdin)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose stderr logs")

    args = parser.parse_args(argv)

    has_question = args.question is not None
    has_file = args.file_path is not None
    mode_count = int(has_question) + int(has_file) + int(args.interactive)
    if mode_count != 1:
        print(
            "Error: provide exactly one mode: positional question, --file, or --interactive.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if args.concurrency < 1 or args.concurrency > 100:
        print("Error: --concurrency must be between 1 and 100.", file=sys.stderr)
        raise SystemExit(1)

    if args.retry < 1:
        print("Error: --retry must be >= 1.", file=sys.stderr)
        raise SystemExit(1)

    if args.no_cache or str(args.cache).lower() == "none":
        args.cache = None

    return args


def ensure_api_key() -> str:
    """Return OPENAI_API_KEY or exit with code 1."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        print("Set it with: export OPENAI_API_KEY=your-key-here", file=sys.stderr)
        raise SystemExit(1)
    return api_key


def load_questions(file_path: str) -> list[str]:
    """Load non-empty questions from file in original order."""
    path = Path(file_path)
    if not path.exists():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        raise SystemExit(2)

    with path.open("r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def load_cache(cache_path: str | None, verbose: bool = False) -> dict[str, dict[str, Any]]:
    """Load cache file into memory; return empty dict on missing/invalid."""
    if cache_path is None:
        return {}

    path = Path(cache_path)
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: failed to read cache {cache_path}: {exc}", file=sys.stderr)
        return {}

    if not isinstance(payload, dict):
        if verbose:
            print("Warning: cache root must be an object, ignoring cache.", file=sys.stderr)
        return {}

    cleaned: dict[str, dict[str, Any]] = {}
    for key, value in payload.items():
        if isinstance(key, str) and isinstance(value, dict):
            cleaned[key] = value
    return cleaned


def save_cache(cache_path: str | None, cache: dict[str, dict[str, Any]]) -> None:
    """Persist cache atomically to disk."""
    if cache_path is None:
        return

    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def strip_code_fences(text: str) -> str:
    """Strip markdown code fences and surrounding text if present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\\s*```$", "", stripped)
    return stripped.strip()


def extract_json_object(text: str) -> str:
    """Extract likely JSON object body from text by outer braces."""
    cleaned = strip_code_fences(text)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        return cleaned
    return cleaned[start : end + 1]


def parse_model_json(raw_text: str) -> dict[str, Any]:
    """Parse model response with recovery attempts."""
    first_attempt = raw_text.strip()
    try:
        payload = json.loads(first_attempt)
    except json.JSONDecodeError:
        second_attempt = extract_json_object(raw_text)
        payload = json.loads(second_attempt)

    if not isinstance(payload, dict):
        raise ValidationError("Model output is not a JSON object", "malformed_json")
    return payload


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize payload schema."""
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValidationError(f"Missing fields: {', '.join(missing)}", "incomplete_response")

    location_name = payload.get("location_name")
    lat = payload.get("latitude")
    lon = payload.get("longitude")

    if location_name is None and lat is None and lon is None:
        lat_f: float | None = None
        lon_f: float | None = None
        location_name_normalized: str | None = None
    else:
        if not isinstance(location_name, str):
            raise ValidationError("location_name must be string or null", "incomplete_response")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            raise ValidationError("Coordinates must be numeric", "incomplete_response")

        lat_f = round(float(lat), 4)
        lon_f = round(float(lon), 4)
        if lat_f < -90.0 or lat_f > 90.0 or lon_f < -180.0 or lon_f > 180.0:
            raise ValidationError("Coordinates out of range", "invalid_coordinates")
        location_name_normalized = location_name

    category = payload.get("category")
    if not isinstance(category, str) or category not in CATEGORIES:
        raise ValidationError("Invalid category", "incomplete_response")

    locations_payload = payload.get("locations")
    normalized_locations: list[dict[str, Any]] = []
    if locations_payload is None:
        if location_name_normalized is not None and lat_f is not None and lon_f is not None:
            normalized_locations = [
                {
                    "location_name": location_name_normalized,
                    "latitude": lat_f,
                    "longitude": lon_f,
                }
            ]
    else:
        if not isinstance(locations_payload, list):
            raise ValidationError("locations must be an array", "incomplete_response")

        for entry in locations_payload:
            if not isinstance(entry, dict):
                raise ValidationError("locations entries must be objects", "incomplete_response")

            missing_location_fields = [field for field in LOCATION_ENTRY_FIELDS if field not in entry]
            if missing_location_fields:
                raise ValidationError("locations entry missing fields", "incomplete_response")

            entry_name = entry.get("location_name")
            entry_lat = entry.get("latitude")
            entry_lon = entry.get("longitude")

            if not isinstance(entry_name, str):
                raise ValidationError("locations.location_name must be string", "incomplete_response")
            if not isinstance(entry_lat, (int, float)) or not isinstance(entry_lon, (int, float)):
                raise ValidationError("locations coordinates must be numeric", "incomplete_response")

            entry_lat_f = round(float(entry_lat), 4)
            entry_lon_f = round(float(entry_lon), 4)
            if entry_lat_f < -90.0 or entry_lat_f > 90.0 or entry_lon_f < -180.0 or entry_lon_f > 180.0:
                raise ValidationError("locations coordinates out of range", "invalid_coordinates")

            normalized_locations.append(
                {
                    "location_name": entry_name,
                    "latitude": entry_lat_f,
                    "longitude": entry_lon_f,
                }
            )

    if location_name_normalized is None and normalized_locations:
        primary = normalized_locations[0]
        location_name_normalized = primary["location_name"]
        lat_f = primary["latitude"]
        lon_f = primary["longitude"]

    if location_name_normalized is not None and lat_f is not None and lon_f is not None:
        primary_tuple = (location_name_normalized, lat_f, lon_f)
        if not any(
            (
                entry["location_name"],
                entry["latitude"],
                entry["longitude"],
            )
            == primary_tuple
            for entry in normalized_locations
        ):
            normalized_locations.insert(
                0,
                {
                    "location_name": location_name_normalized,
                    "latitude": lat_f,
                    "longitude": lon_f,
                },
            )

    # Deduplicate while preserving order, then enforce max 3 locations.
    deduped_locations: list[dict[str, Any]] = []
    seen_location_keys: set[tuple[str, float, float]] = set()
    for entry in normalized_locations:
        key = (entry["location_name"], entry["latitude"], entry["longitude"])
        if key in seen_location_keys:
            continue
        seen_location_keys.add(key)
        deduped_locations.append(entry)
    normalized_locations = deduped_locations[:3]

    normalized: dict[str, Any] = {
        "entity": payload.get("entity") if isinstance(payload.get("entity"), str) else None,
        "reasoning": payload.get("reasoning") if isinstance(payload.get("reasoning"), str) else None,
        "location_name": location_name_normalized,
        "latitude": lat_f,
        "longitude": lon_f,
        "locations": normalized_locations,
        "category": category,
    }

    if normalized["entity"] is None or normalized["reasoning"] is None:
        raise ValidationError("Required string fields missing", "incomplete_response")

    return normalized


def is_locationless_market_question(question: str, category: str) -> bool:
    """Detect pure market-threshold questions that have no clear physical anchor."""
    if category not in {"crypto", "finance"}:
        return False

    lowered = question.lower()
    patterns = [
        r"\breach\s*\$?\d",
        r"\bhit\s*\$?\d",
        r"\bprice\b",
        r"\btrading\s+above\b",
        r"\btrading\s+below\b",
        r"\babove\s*\$?\d",
        r"\bbelow\s*\$?\d",
    ]
    return any(re.search(pattern, lowered) is not None for pattern in patterns)


def is_global_related_question(question: str, category: str) -> bool:
    """Detect globally scoped questions that should not map to one location."""
    lowered = question.lower()

    global_patterns = [
        r"\bglobal\b",
        r"\bworldwide\b",
        r"\bworld\b",
        r"\bany country\b",
        r"\bany nation\b",
        r"\banywhere\b",
        r"\bin the world\b",
        r"\bworld war\b",
        r"\bnew pandemic\b",
        r"\bglobal pandemic\b",
        r"\bglobal recession\b",
        r"\bplanet\b",
    ]

    if any(re.search(pattern, lowered) is not None for pattern in global_patterns):
        return True

    if category in {"science", "natural_disaster"}:
        broad_science_patterns = [
            r"\brecord\b",
            r"\bwarmest\b",
            r"\bhottest\b",
            r"\bearthquake\b",
            r"\btsunami\b",
            r"\bvolcanic\b",
        ]
        if any(re.search(pattern, lowered) is not None for pattern in broad_science_patterns):
            return True

    return False


def location_specificity_score(location_name: str | None) -> int:
    """Score how specific a location label appears."""
    if not isinstance(location_name, str) or not location_name.strip():
        return 0

    lowered = location_name.lower().strip()
    score = 0

    if "," in lowered:
        score += 1

    specific_markers = [
        "stadium",
        "arena",
        "center",
        "centre",
        "building",
        "palace",
        "capitol",
        "parliament",
        "house",
        "hq",
        "headquarters",
        "office",
        "ministry",
        "court",
        "exchange",
        "bank",
        "district",
        "street",
        "avenue",
        "road",
        "boulevard",
        "tower",
        "campus",
        "base",
        "strait",
        "gulf",
        "sea",
    ]
    if any(marker in lowered for marker in specific_markers):
        score += 2

    words = [token for token in re.split(r"\s+", lowered) if token]
    if len(words) >= 3:
        score += 1

    return score


def should_refine_result(question: str, result: dict[str, Any]) -> bool:
    """Determine whether an LLM result appears too generic and should be refined."""
    if "error" in result:
        return False

    category = result.get("category")
    if not isinstance(category, str):
        return False

    if category == "crypto" or is_global_related_question(question, category):
        return False

    lowered_q = question.lower()
    multi_location_signals = [
        " vs ",
        " x ",
        " versus ",
        " between ",
        " and ",
        " bilateral",
        " coalition",
        " alliance",
        " trade deal",
        " ceasefire",
        " summit",
        " finals",
        " matchup",
    ]
    likely_multi_location = any(signal in lowered_q for signal in multi_location_signals)

    military_or_policy = any(
        keyword in lowered_q
        for keyword in [
            "military",
            "clash",
            "strike",
            "war",
            "invasion",
            "attack",
            "policy",
            "bill",
            "law",
            "regulation",
            "sanction",
            "congress",
            "parliament",
        ]
    )
    sports = category == "sports"
    finance = category == "finance"

    if not (military_or_policy or sports or finance):
        return False

    location_name = result.get("location_name")
    score = location_specificity_score(location_name if isinstance(location_name, str) else None)
    locations = result.get("locations")
    location_count = len(locations) if isinstance(locations, list) else 0

    if score <= 1:
        return True

    if military_or_policy and location_count < 2 and (" x " in lowered_q or " vs " in lowered_q):
        return True

    if likely_multi_location and location_count < 2:
        return True

    return False


async def refine_result(
    client: AsyncOpenAI,
    model: str,
    question: str,
    current_result: dict[str, Any],
    verbose: bool,
) -> dict[str, Any]:
    """Try one refinement pass to improve location specificity."""
    try:
        response = await client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=260,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": REFINEMENT_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": question,
                            "previous_result": {
                                "entity": current_result.get("entity"),
                                "reasoning": current_result.get("reasoning"),
                                "location_name": current_result.get("location_name"),
                                "latitude": current_result.get("latitude"),
                                "longitude": current_result.get("longitude"),
                                "locations": current_result.get("locations"),
                                "category": current_result.get("category"),
                            },
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )

        message = response.choices[0].message
        content = extract_message_content(message.content)
        parsed = parse_model_json(content)
        normalized = validate_payload(parsed)
        candidate = to_output_result(question, normalized, source="llm")

        current_score = location_specificity_score(
            current_result.get("location_name") if isinstance(current_result.get("location_name"), str) else None
        )
        candidate_score = location_specificity_score(
            candidate.get("location_name") if isinstance(candidate.get("location_name"), str) else None
        )

        current_locations = current_result.get("locations")
        candidate_locations = candidate.get("locations")
        current_count = len(current_locations) if isinstance(current_locations, list) else 0
        candidate_count = len(candidate_locations) if isinstance(candidate_locations, list) else 0

        if candidate_score > current_score or candidate_count > current_count:
            return candidate
    except Exception as exc:  # noqa: BLE001
        if verbose:
            print(f"Refinement skipped for question due to: {exc}", file=sys.stderr)

    return current_result


def apply_locationless_override(question: str, result: dict[str, Any]) -> dict[str, Any]:
    """Force null location fields for clear locationless market questions."""
    if "error" in result:
        return result

    category = result.get("category")
    if not isinstance(category, str):
        return result

    if category == "crypto":
        updated = dict(result)
        updated["location_name"] = None
        updated["latitude"] = None
        updated["longitude"] = None
        updated["locations"] = []
        return updated

    if is_global_related_question(question, category):
        updated = dict(result)
        updated["location_name"] = None
        updated["latitude"] = None
        updated["longitude"] = None
        updated["locations"] = []
        return updated

    if not is_locationless_market_question(question, category):
        return result

    updated = dict(result)
    updated["location_name"] = None
    updated["latitude"] = None
    updated["longitude"] = None
    updated["locations"] = []
    return updated


def build_error_result(question: str, error: str, source: str = "llm") -> dict[str, Any]:
    """Build standardized failed result row."""
    return {
        "question": question,
        "entity": None,
        "reasoning": None,
        "location_name": None,
        "latitude": None,
        "longitude": None,
        "locations": None,
        "category": None,
        "source": source,
        "error": error,
    }


def to_output_result(question: str, payload: dict[str, Any], source: str) -> dict[str, Any]:
    """Ensure canonical output row format including question."""
    if "error" in payload:
        return build_error_result(question, str(payload.get("error")), source=source)
    return {
        "question": question,
        "entity": payload.get("entity"),
        "reasoning": payload.get("reasoning"),
        "location_name": payload.get("location_name"),
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "locations": payload.get("locations"),
        "category": payload.get("category"),
        "source": source,
    }


def to_cache_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Strip question/error wrapper before persisting successful cache entry."""
    return {
        "entity": result["entity"],
        "reasoning": result["reasoning"],
        "location_name": result["location_name"],
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "locations": result["locations"],
        "category": result["category"],
    }


def normalize_cached_result(question: str, cached_payload: dict[str, Any]) -> dict[str, Any] | None:
    """Validate cache row; return normalized output row or None if invalid."""
    try:
        normalized = validate_payload(cached_payload)
    except ValidationError:
        return None
    return to_output_result(question, normalized, source="cache")


def extract_message_content(content: Any) -> str:
    """Extract string content from OpenAI message payload variants."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
            else:
                text_attr = getattr(item, "text", None)
                if isinstance(text_attr, str):
                    parts.append(text_attr)
        return "".join(parts)
    return ""


def compute_rate_limit_delay(attempt: int, exc: Exception | None = None) -> float:
    """Compute backoff delay with optional Retry-After header and jitter."""
    base = min(2 ** (attempt - 1), 30)
    retry_after = None

    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is not None:
        retry_after_value = headers.get("retry-after")
        if isinstance(retry_after_value, str):
            try:
                retry_after = float(retry_after_value)
            except ValueError:
                retry_after = None

    delay = max(base, retry_after) if isinstance(retry_after, (int, float)) else base
    jitter = random.uniform(0.0, 0.4)
    return delay + jitter


async def geocode_question(
    client: AsyncOpenAI,
    model: str,
    question: str,
    max_retries: int,
    verbose: bool,
) -> dict[str, Any]:
    """Geocode one question with retries and robust JSON validation."""
    last_error = "failed after retries"

    for attempt in range(1, max_retries + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                temperature=0,
                max_tokens=260,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ],
            )

            message = response.choices[0].message
            content = extract_message_content(message.content)
            parsed = parse_model_json(content)
            normalized = validate_payload(parsed)
            result = to_output_result(question, normalized, source="llm")
            if should_refine_result(question, result):
                result = await refine_result(client, model, question, result, verbose)
            return apply_locationless_override(question, result)

        except RateLimitError:
            last_error = "rate limit"
            if attempt < max_retries:
                await asyncio.sleep(compute_rate_limit_delay(attempt))
            continue
        except APIStatusError as exc:
            if exc.status_code == 429:
                last_error = "rate limit"
                if attempt < max_retries:
                    await asyncio.sleep(compute_rate_limit_delay(attempt, exc))
                continue
            last_error = f"api status error ({exc.status_code})"
            if attempt < max_retries:
                await asyncio.sleep(1)
            continue
        except (APIConnectionError, APITimeoutError):
            last_error = "api connection error"
            if attempt < max_retries:
                await asyncio.sleep(1)
            continue
        except json.JSONDecodeError:
            last_error = "malformed json"
            if attempt < max_retries:
                await asyncio.sleep(1)
            continue
        except ValidationError as exc:
            if exc.code == "invalid_coordinates":
                last_error = "invalid coordinates"
            elif exc.code == "incomplete_response":
                last_error = "incomplete response"
            else:
                last_error = "malformed json"
            if attempt < max_retries:
                await asyncio.sleep(1)
            continue
        except APIError as exc:
            last_error = f"api error: {type(exc).__name__}"
            if attempt < max_retries:
                await asyncio.sleep(1)
            continue
        except Exception as exc:  # noqa: BLE001
            last_error = f"unexpected error: {type(exc).__name__}"
            if verbose:
                print(f"Unexpected error on question: {question}\n{exc}", file=sys.stderr)
            if attempt < max_retries:
                await asyncio.sleep(1)
            continue

    return build_error_result(question, last_error, source="llm")


async def geocode_question_guarded(
    semaphore: asyncio.Semaphore,
    client: AsyncOpenAI,
    model: str,
    question: str,
    max_retries: int,
    verbose: bool,
) -> tuple[str, dict[str, Any]]:
    """Run geocoding under semaphore and return question + result."""
    async with semaphore:
        result = await geocode_question(
            client=client,
            model=model,
            question=question,
            max_retries=max_retries,
            verbose=verbose,
        )
        return question, result


def print_progress(processed: int, total: int, cache_hits: int) -> None:
    """Print current processing status to stderr."""
    percent = (processed / total * 100.0) if total else 100.0
    print(
        f"Processing: {processed}/{total} ({percent:.1f}%) [cache: {cache_hits} hits]",
        file=sys.stderr,
    )


async def run_single(args: argparse.Namespace, client: AsyncOpenAI) -> int:
    """Execute single-question mode."""
    assert args.question is not None
    question = args.question

    cache = load_cache(args.cache, verbose=args.verbose)
    if args.cache is not None and question in cache:
        cached_result = normalize_cached_result(question, cache[question])
        if cached_result is not None:
            write_output(apply_locationless_override(question, cached_result), args.output_path)
            return 0

    result = await geocode_question(
        client=client,
        model=args.model,
        question=question,
        max_retries=args.retry,
        verbose=args.verbose,
    )

    if args.cache is not None and "error" not in result:
        cache[question] = to_cache_payload(result)
        save_cache(args.cache, cache)

    write_output(result, args.output_path)
    return 0


async def run_interactive(args: argparse.Namespace, client: AsyncOpenAI) -> int:
    """Execute continuous interactive mode from stdin."""
    cache = load_cache(args.cache, verbose=args.verbose)
    prompt = "geolocate> "

    print("Interactive mode ready. Enter a question per line. Type 'exit' or 'quit' to stop.", file=sys.stderr)

    while True:
        try:
            sys.stderr.write(prompt)
            sys.stderr.flush()
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            break

        if line == "":
            break

        question = line.strip()
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            break

        if args.cache is not None and question in cache:
            cached_result = normalize_cached_result(question, cache[question])
            if cached_result is not None:
                write_output(apply_locationless_override(question, cached_result), None)
                continue

        result = await geocode_question(
            client=client,
            model=args.model,
            question=question,
            max_retries=args.retry,
            verbose=args.verbose,
        )
        write_output(result, None)

        if args.cache is not None and "error" not in result:
            cache[question] = to_cache_payload(result)
            save_cache(args.cache, cache)

    if args.cache is not None:
        save_cache(args.cache, cache)
    return 0


async def run_batch(args: argparse.Namespace, client: AsyncOpenAI) -> int:
    """Execute batch mode with deduping, cache, and bounded concurrency."""
    assert args.file_path is not None
    questions = load_questions(args.file_path)

    if not questions:
        write_output([], args.output_path)
        print("Done: 0/0 (100.0%) [cache: 0 hits, api: 0 calls, errors: 0]", file=sys.stderr)
        return 0

    unique_questions = list(dict.fromkeys(questions))
    total_unique = len(unique_questions)

    cache = load_cache(args.cache, verbose=args.verbose)
    results_by_question: dict[str, dict[str, Any]] = {}

    processed = 0
    cache_hits = 0
    api_calls = 0
    errors = 0
    new_cache_entries = 0

    misses: list[str] = []
    for question in unique_questions:
        cached = cache.get(question)
        if args.cache is not None and isinstance(cached, dict):
            result = normalize_cached_result(question, cached)
            if result is not None:
                results_by_question[question] = apply_locationless_override(question, result)
                processed += 1
                cache_hits += 1
                if "error" in result:
                    errors += 1
                print_progress(processed, total_unique, cache_hits)
                continue
            if args.verbose:
                print(f"Warning: invalid cache entry for question: {question}", file=sys.stderr)
            cache.pop(question, None)
        else:
            pass
        misses.append(question)

    semaphore = asyncio.Semaphore(args.concurrency)
    tasks = [
        asyncio.create_task(
            geocode_question_guarded(
                semaphore=semaphore,
                client=client,
                model=args.model,
                question=question,
                max_retries=args.retry,
                verbose=args.verbose,
            )
        )
        for question in misses
    ]

    for task in asyncio.as_completed(tasks):
        question, result = await task
        results_by_question[question] = result
        processed += 1
        api_calls += 1
        if "error" in result:
            errors += 1
        else:
            if args.cache is not None:
                cache[question] = to_cache_payload(result)
                new_cache_entries += 1
                if new_cache_entries % 50 == 0:
                    save_cache(args.cache, cache)
        print_progress(processed, total_unique, cache_hits)

    if args.cache is not None and new_cache_entries > 0:
        save_cache(args.cache, cache)

    output_rows = [results_by_question[q] for q in questions]
    write_output(output_rows, args.output_path)

    total_rows = len(output_rows)
    print(
        f"Done: {processed}/{total_unique} (100.0%) [cache: {cache_hits} hits, api: {api_calls} calls, errors: {errors}]",
        file=sys.stderr,
    )

    if errors > 0:
        print(f"Warning: {errors}/{total_rows} questions failed. See error fields in output.", file=sys.stderr)
        return 3

    return 0


def write_output(payload: Any, output_path: str | None) -> None:
    """Write JSON payload to stdout or file."""
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    if output_path is None:
        print(serialized)
        return

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(serialized)


async def async_main(argv: list[str]) -> int:
    """Async CLI entrypoint."""
    args = parse_args(argv)
    api_key = ensure_api_key()
    client = AsyncOpenAI(api_key=api_key)

    if args.file_path:
        return await run_batch(args, client)
    if args.interactive:
        return await run_interactive(args, client)
    return await run_single(args, client)


def main() -> None:
    """Synchronous wrapper around async main."""
    try:
        exit_code = asyncio.run(async_main(sys.argv[1:]))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
