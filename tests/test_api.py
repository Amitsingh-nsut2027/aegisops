import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from api import create_app, get_repository
from auth import AuthSettings, require_event_reader

TEST_SETTINGS = AuthSettings(secret="unit-test-only-signing-key-never-for-deployment")


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.engine, self.repository = Mock(), Mock()
        self.row = dict(event_id="a" * 64, event_type="cpu.high.v1", source="simulator",
                        resource_id="simulated/api", observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                        received_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                        payload={"cpu_evidence": [91, 92, 93], "severity": "warning"})
        self.app = create_app(lambda: self.engine, lambda: TEST_SETTINGS)
        self.app.dependency_overrides[require_event_reader] = lambda: None
        self.app.dependency_overrides[get_repository] = lambda: self.repository
        self.role_check = patch("api.assert_reader_role")
        self.role_check.start()
        self.client = TestClient(self.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.role_check.stop()

    def test_health_needs_no_repository(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "local-simulation")
        self.repository.ready.assert_not_called()
        self.assertEqual(len(response.headers["X-Request-ID"]), 32)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_paginated_list_with_filter(self):
        self.repository.list_events.return_value = [self.row, {**self.row, "event_id": "b" * 64}]
        response = self.client.get("/events?limit=1&offset=2&source=simulator")
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["returned"], 1)
        self.assertTrue(body["has_more"])
        self.assertEqual(body["items"][0]["event_id"], "a" * 64)
        self.repository.list_events.assert_called_once_with(1, 2, "simulator")

    def test_empty_list_is_not_an_error(self):
        self.repository.list_events.return_value = []
        response = self.client.get("/events")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
        self.assertFalse(response.json()["has_more"])

    def test_invalid_queries_rejected_before_database(self):
        for query in ["limit=0", "limit=101", "offset=-1", "offset=10001", "source=aws", "limit=abc"]:
            with self.subTest(query=query):
                self.assertEqual(self.client.get("/events?" + query).status_code, 422)
        self.repository.list_events.assert_not_called()

    def test_detail_found_missing_and_invalid(self):
        self.repository.get_event.return_value = self.row
        self.assertEqual(self.client.get("/events/" + "a" * 64).status_code, 200)
        self.repository.get_event.return_value = None
        self.assertEqual(self.client.get("/events/" + "b" * 64).status_code, 404)
        self.assertEqual(self.client.get("/events/not-an-id").status_code, 422)

    def test_database_failures_are_sanitized(self):
        self.repository.list_events.side_effect = OperationalError("SECRET_SQL", {}, Exception("SECRET_PASSWORD"))
        response = self.client.get("/events")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database temporarily unavailable"})
        self.assertNotIn("SECRET", response.text)

    def test_readiness_checks_database_and_reports_failure(self):
        self.assertEqual(self.client.get("/ready").status_code, 200)
        self.repository.ready.assert_called_once()
        self.repository.ready.side_effect = OperationalError("", {}, Exception("offline"))
        self.assertEqual(self.client.get("/ready").status_code, 503)

    def test_no_write_route(self):
        self.assertEqual(self.client.post("/events", json={}).status_code, 405)

    def test_engine_disposed_and_admin_role_rejected(self):
        engine = Mock()
        with patch("api.assert_reader_role", side_effect=RuntimeError("read-only role required")):
            with self.assertRaises(RuntimeError):
                with TestClient(create_app(lambda: engine, lambda: TEST_SETTINGS)):
                    pass
        engine.dispose.assert_called_once()


if __name__ == "__main__":
    unittest.main()
