import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import jwt
from fastapi.testclient import TestClient

from api import create_app, get_repository
from auth import AuthSettings, issue_viewer_token

TEST_SECRET = "unit-test-signing-key-only-never-use-in-production-0123456789-abcdef"


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.settings = AuthSettings(secret=TEST_SECRET)
        self.repository = Mock()
        self.repository.list_events.return_value = []
        self.app = create_app(lambda: Mock(), lambda: self.settings)
        self.app.dependency_overrides[get_repository] = lambda: self.repository
        self.role_check = patch("api.assert_reader_role")
        self.role_check.start()
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.token = issue_viewer_token(self.settings)

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.role_check.stop()

    def request(self, token):
        return self.client.get("/events", headers={"Authorization": "Bearer " + token})

    def changed_token(self, **changes):
        claims = jwt.decode(self.token, options={"verify_signature": False})
        claims.update(changes)
        return jwt.encode(claims, TEST_SECRET, algorithm="HS256")

    def test_missing_token_denied_before_repository(self):
        for path in ["/events", "/events/" + "a" * 64]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")
        self.repository.list_events.assert_not_called()
        self.repository.get_event.assert_not_called()

    def test_viewer_can_read_and_lifetime_is_fifteen_minutes(self):
        response = self.request(self.token)
        self.assertEqual(response.status_code, 200)
        claims = jwt.decode(self.token, TEST_SECRET, algorithms=["HS256"],
                            issuer=self.settings.issuer, audience=self.settings.audience)
        self.assertEqual(claims["exp"] - claims["iat"], 900)
        self.assertEqual(claims["role"], "viewer")

    def test_expired_malformed_and_wrong_signature_rejected(self):
        expired = issue_viewer_token(self.settings, now=datetime.now(timezone.utc) - timedelta(hours=1))
        wrong_key = issue_viewer_token(AuthSettings(secret="other-unit-test-secret-012345678901234567890123456789"))
        for token in [expired, wrong_key, "not-a-token"]:
            with self.subTest(case="invalid credentials"):
                response = self.request(token)
                self.assertEqual(response.status_code, 401)
                self.assertNotIn(token, response.text)
        self.repository.list_events.assert_not_called()

    def test_wrong_issuer_audience_and_extended_lifetime_rejected(self):
        for changes in [dict(iss="other-issuer"), dict(aud="other-api"),
                        dict(exp=int(datetime.now(timezone.utc).timestamp()) + 86400),
                        dict(role=True), dict(admin=True)]:
            with self.subTest(changes=changes):
                self.assertEqual(self.request(self.changed_token(**changes)).status_code, 401)

    def test_unknown_role_forbidden(self):
        self.assertEqual(self.request(self.changed_token(role="unassigned")).status_code, 403)
        self.repository.list_events.assert_not_called()

    def test_missing_required_claim_and_other_algorithm_rejected(self):
        claims = jwt.decode(self.token, options={"verify_signature": False})
        del claims["role"]
        self.assertEqual(self.request(jwt.encode(claims, TEST_SECRET, algorithm="HS256")).status_code, 401)
        self.assertEqual(self.request(jwt.encode(claims, TEST_SECRET, algorithm="HS512")).status_code, 401)

    def test_health_and_docs_public_but_openapi_marks_events_protected(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/docs").status_code, 200)
        schema = self.client.get("/openapi.json").json()
        self.assertEqual(schema["paths"]["/events"]["get"]["security"], [{"ViewerJWT": []}])
        self.assertNotIn("security", schema["paths"]["/health"]["get"])

    def test_short_secret_and_naive_issue_time_rejected(self):
        with self.assertRaises(ValueError):
            AuthSettings(secret="short")
        with self.assertRaises(ValueError):
            issue_viewer_token(self.settings, now=datetime(2026, 1, 1))
        self.assertNotIn(TEST_SECRET, repr(self.settings))


if __name__ == "__main__":
    unittest.main()
