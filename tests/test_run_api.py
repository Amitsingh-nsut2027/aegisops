import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from api import create_app, get_run_repository
from auth import AuthSettings, issue_viewer_token


class RunApiTests(unittest.TestCase):
    def setUp(self):
        self.settings = AuthSettings(secret="run-api-unit-test-key-not-for-deployment")
        self.repository = Mock()
        self.app = create_app(lambda: Mock(), lambda: self.settings)
        self.app.dependency_overrides[get_run_repository] = lambda: self.repository
        self.guard = patch("api.assert_reader_role")
        self.guard.start()
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.headers = {"Authorization": "Bearer " + issue_viewer_token(self.settings)}
        instant = datetime.now(timezone.utc)
        self.row = dict(run_id="a" * 32, event_id="b" * 64, state="needs_evidence",
                        started_at=instant, finished_at=instant, payload={"simulated": True})

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.guard.stop()

    def test_authentication_required_for_list_and_detail(self):
        for path in ["/investigations", "/investigations/" + "a" * 32]:
            self.assertEqual(self.client.get(path).status_code, 401)
        self.repository.list_runs.assert_not_called()
        self.repository.get_run.assert_not_called()

    def test_viewer_pagination_and_event_filter(self):
        self.repository.list_runs.return_value = [self.row, {**self.row, "run_id": "c" * 32}]
        response = self.client.get("/investigations?limit=1&offset=2&event_id=" + "b" * 64,
                                   headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["has_more"])
        self.assertEqual(response.json()["returned"], 1)
        self.repository.list_runs.assert_called_once_with(1, 2, "b" * 64)

    def test_detail_and_missing(self):
        self.repository.get_run.return_value = self.row
        self.assertEqual(self.client.get("/investigations/" + "a" * 32, headers=self.headers).status_code, 200)
        self.repository.get_run.return_value = None
        self.assertEqual(self.client.get("/investigations/" + "c" * 32, headers=self.headers).status_code, 404)

    def test_input_validation_and_no_http_creation(self):
        for suffix in ["?limit=0", "?limit=101", "?offset=-1", "?offset=10001", "?event_id=bad", "/bad"]:
            self.assertEqual(self.client.get("/investigations" + suffix, headers=self.headers).status_code, 422)
        self.repository.list_runs.assert_not_called()
        self.repository.get_run.assert_not_called()
        self.assertEqual(self.client.post("/investigations", headers=self.headers, json={}).status_code, 405)

    def test_database_error_sanitized(self):
        self.repository.list_runs.side_effect = OperationalError("SECRET", {}, Exception("PASSWORD"))
        response = self.client.get("/investigations", headers=self.headers)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("SECRET", response.text)
