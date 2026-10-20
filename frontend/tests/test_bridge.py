"""Boundary tests for the local-only, read-only browser bridge."""
import importlib.util
import json
from pathlib import Path
from threading import Thread
import tempfile
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
from functools import partial

spec = importlib.util.spec_from_file_location('workbench_bridge', Path(__file__).resolve().parents[2] / 'scripts' / 'serve_frontend.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = bridge.ThreadingHTTPServer(('127.0.0.1', 0), partial(bridge.WorkbenchHandler, directory=str(bridge.PUBLIC)))
        bridge.PORT = cls.server.server_port
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{bridge.PORT}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()

    def request(self, path='/', headers=None):
        try:
            with urlopen(Request(self.url + path, headers=headers or {})) as result:
                return result.status, result.read(), result.headers
        except HTTPError as error:
            return error.code, error.read(), error.headers

    def test_static_ui_and_security_headers(self):
        status, body, headers = self.request()
        self.assertEqual(status, 200)
        self.assertIn(b'Incident workbench', body)
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertEqual(headers['Cache-Control'], 'no-store')

    def test_host_and_cross_site_fetch_are_rejected(self):
        self.assertEqual(self.request('/api/events', {'Host':'attacker.example'})[0], 403)
        self.assertEqual(self.request('/api/events', {'Sec-Fetch-Site':'cross-site'})[0], 403)

    def test_bridge_does_not_proxy_unapproved_paths(self):
        for path in ['/api/health', '/api/http://example.com', '/api/events/not-an-id']:
            self.assertEqual(self.request(path)[0], 404)

    def test_hidden_or_private_paths_are_never_served(self):
        for path in ['/.local/viewer-token.txt', '/../.env', '/%2e%2e/.env.auth', '/assets/']:
            self.assertEqual(self.request(path)[0], 404)

    def test_missing_token_is_a_session_error(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bridge, 'TOKEN', Path(directory)/'missing'):
            status, body, _ = self.request('/api/events')
        self.assertEqual(status, 401)
        self.assertNotIn(b'viewer-token.txt', body)

    def test_token_is_used_only_in_upstream_header(self):
        class Reply:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return b'{"items": []}'
        with tempfile.TemporaryDirectory() as directory:
            token = Path(directory)/'token'; token.write_text('private-test-token')
            with patch.object(bridge, 'TOKEN', token), patch.object(bridge, 'urlopen', return_value=Reply()) as upstream:
                status, body, _ = self.request('/api/events?limit=1')
                request = upstream.call_args.args[0]
                self.assertEqual(request.get_header('Authorization'), 'Bearer private-test-token')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {'items': []})
        self.assertNotIn(b'private-test-token', body)


if __name__ == '__main__':
    unittest.main()
