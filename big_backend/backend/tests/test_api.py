import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import create_app


SAMPLE_RESULTS = [
    {
        "question": "Will there be a major event in New York City?",
        "location_name": "New York City, New York, United States",
        "latitude": 40.7128,
        "longitude": -74.0060,
    },
    {
        "question": "Will Austin host SXSW next year?",
        "location_name": "Austin, Texas, United States",
    },
    {
        "question": "Will MSG host a sold-out show this quarter?",
        "location_name": "Madison Square Garden, New York City, New York, United States",
    },
    {
        "question": "Will Alaska host an energy summit this year?",
        "location_name": "Alaska, United States",
    },
    {
        "question": "Will Maine host a fishing summit this year?",
        "location_name": "Maine, United States",
    },
    {
        "question": "Will Seattle host a major conference?",
        "location_name": "Seattle, Washington, United States",
    },
]

SAMPLE_CACHE = {
    "Will Dallas host a new event?": {
        "location_name": "Dallas, Texas, United States",
        "latitude": 32.7767,
        "longitude": -96.797,
    }
}


class ApiEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.results_path = Path(cls.temp_dir.name) / "results.json"
        cls.cache_path = Path(cls.temp_dir.name) / "cache.json"

        cls.results_path.write_text(json.dumps(SAMPLE_RESULTS), encoding="utf-8")
        cls.cache_path.write_text(json.dumps(SAMPLE_CACHE), encoding="utf-8")

        cls.original_env = {
            "POLYWORLD_RESULTS_FILE": os.getenv("POLYWORLD_RESULTS_FILE"),
            "POLYWORLD_CACHE_FILE": os.getenv("POLYWORLD_CACHE_FILE"),
            "POLYWORLD_CORS_ORIGINS": os.getenv("POLYWORLD_CORS_ORIGINS"),
            "POLYWORLD_CORS_ALLOW_CREDENTIALS": os.getenv("POLYWORLD_CORS_ALLOW_CREDENTIALS"),
        }

        os.environ["POLYWORLD_RESULTS_FILE"] = str(cls.results_path)
        os.environ["POLYWORLD_CACHE_FILE"] = str(cls.cache_path)
        os.environ["POLYWORLD_CORS_ORIGINS"] = "http://localhost:5173"
        os.environ["POLYWORLD_CORS_ALLOW_CREDENTIALS"] = "false"

        cls.client = TestClient(create_app())

    @classmethod
    def tearDownClass(cls) -> None:
        for key, value in cls.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cls.temp_dir.cleanup()

    def test_health_returns_service_metadata(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertGreaterEqual(payload["records"], 3)
        self.assertIn("indexed_tokens", payload)

    def test_markets_coordinates_returns_all_points(self) -> None:
        response = self.client.get("/api/v1/markets/coordinates")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("count", payload)
        self.assertIn("coordinates", payload)
        self.assertGreaterEqual(payload["count"], 2)

        questions = {row["question"] for row in payload["coordinates"]}
        self.assertIn("Will there be a major event in New York City?", questions)
        self.assertIn("Will Dallas host a new event?", questions)

    def test_markets_requires_non_blank_query(self) -> None:
        response = self.client.get("/markets", params={"query": "   "})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "query is required")

    def test_markets_rejects_overly_long_query(self) -> None:
        response = self.client.get("/markets", params={"query": "x" * 201})
        self.assertEqual(response.status_code, 422)

    def test_markets_alias_search_works(self) -> None:
        response = self.client.get("/markets", params={"query": "nyc"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["count"], 1)
        questions = [row["question"] for row in payload["results"]]
        self.assertIn("Will there be a major event in New York City?", questions)

    def test_events_by_location_strict_and_pagination(self) -> None:
        response = self.client.get(
            "/api/v1/events/by-location",
            params={"location": "seattle", "strict": "true", "limit": 1, "offset": 0},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["mode"], "exact")
        self.assertEqual(payload["limit"], 1)
        self.assertEqual(payload["offset"], 0)
        self.assertIn("has_more", payload)
        self.assertGreaterEqual(payload["count"], 1)

    def test_events_by_location_formatted_location_fallback(self) -> None:
        response = self.client.get(
            "/api/v1/events/by-location",
            params={
                "location": "New York City, New York, United States",
                "strict": "false",
                "limit": 10,
                "offset": 0,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["mode"], "exact")
        self.assertTrue(payload["strict"])
        self.assertGreaterEqual(payload["count"], 1)
        questions = [row["question"] for row in payload["results"]]
        self.assertIn("Will there be a major event in New York City?", questions)

    def test_events_by_location_no_fallback_for_unmatched_city(self) -> None:
        response = self.client.get(
            "/api/v1/events/by-location",
            params={
                "location": "Nonexistent City, United States",
                "strict": "false",
                "limit": 10,
                "offset": 0,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["mode"], "exact")
        self.assertTrue(payload["strict"])
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["results"], [])

    def test_events_by_place_city_scope(self) -> None:
        response = self.client.post(
            "/api/v1/events/by-place",
            json={
                "name": "Austin",
                "place_name": "Austin, Texas, United States",
                "place_type": ["place"],
                "strict_intent": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["matched_scope"], "city")
        self.assertGreaterEqual(payload["count"], 1)
        questions = [row["question"] for row in payload["results"]]
        self.assertIn("Will Austin host SXSW next year?", questions)

    def test_events_by_place_poi_scope(self) -> None:
        response = self.client.post(
            "/api/v1/events/by-place",
            json={
                "name": "Madison Square Garden",
                "place_name": "Madison Square Garden, New York City, New York, United States",
                "place_type": ["poi"],
                "strict_intent": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["matched_scope"], "poi")
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["question"], "Will MSG host a sold-out show this quarter?")

    def test_events_by_place_poi_miss_returns_zero(self) -> None:
        response = self.client.post(
            "/api/v1/events/by-place",
            json={
                "name": "Unknown Stadium",
                "place_name": "Unknown Stadium, New York City, New York, United States",
                "place_type": ["poi"],
                "strict_intent": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["matched_scope"], "poi")
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["results"], [])

    def test_events_by_place_region_does_not_widen_to_country(self) -> None:
        response = self.client.post(
            "/api/v1/events/by-place",
            json={
                "name": "Alaska",
                "place_name": "Alaska, United States",
                "place_type": ["region"],
                "region": "Alaska",
                "country": "United States",
                "strict_intent": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["matched_scope"], "region")
        questions = [row["question"] for row in payload["results"]]
        self.assertIn("Will Alaska host an energy summit this year?", questions)
        self.assertNotIn("Will Maine host a fishing summit this year?", questions)

    def test_events_by_location_rejects_invalid_pagination(self) -> None:
        response = self.client.get(
            "/api/v1/events/by-location",
            params={"location": "seattle", "limit": 1001},
        )
        self.assertEqual(response.status_code, 422)

        response = self.client.get(
            "/api/v1/events/by-location",
            params={"location": "seattle", "offset": -1},
        )
        self.assertEqual(response.status_code, 422)

    def test_cors_preflight_allows_configured_origin(self) -> None:
        response = self.client.options(
            "/markets",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5173")


if __name__ == "__main__":
    unittest.main()
