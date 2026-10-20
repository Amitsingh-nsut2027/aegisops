"""Local-only static workbench and read-only API bridge. Never serves token files."""
import json
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "frontend"
TOKEN = ROOT / ".local" / "viewer-token.txt"
PORT = 5173


class WorkbenchHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        super().end_headers()

    def reply(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Guard the local credential bridge against cross-site fetches and DNS rebinding.
        if self.headers.get("Host") not in (f"127.0.0.1:{PORT}", f"localhost:{PORT}"):
            return self.reply(403, {"detail": "Local host required"})
        if self.headers.get("Sec-Fetch-Site") not in (None, "none", "same-origin"):
            return self.reply(403, {"detail": "Same-origin requests required"})
        parsed = urlsplit(self.path)
        if parsed.path.startswith("/api/"):
            path = parsed.path[4:]
            if not re.fullmatch(r"/(events(?:/[a-f0-9]{64})?|investigations(?:/[a-f0-9]{32})?)", path):
                return self.reply(404, {"detail": "Unknown read endpoint"})
            try:
                token = TOKEN.read_text().strip()
                if not token or len(token) > 8192:
                    raise ValueError("Invalid token file")
            except (OSError, ValueError):
                return self.reply(401, {"detail": "Local viewer session required"})
            endpoint = "http://127.0.0.1:8000" + path + ("?" + parsed.query if parsed.query else "")
            try:
                request = Request(endpoint, headers={"Authorization": "Bearer " + token})
                with urlopen(request, timeout=8) as response:
                    # The bridge accepts only bounded API JSON, never forwards credentials/headers.
                    body = response.read(8 * 1024 * 1024 + 1)
                    if len(body) > 8 * 1024 * 1024:
                        return self.reply(502, {"detail": "Response exceeds local preview limit"})
                    return self.reply(response.status, json.loads(body))
            except HTTPError as error:
                return self.reply(error.code, {"detail": "Session expired" if error.code == 401 else "API request failed"})
            except (URLError, TimeoutError, OSError, ValueError):
                return self.reply(503, {"detail": "API unavailable"})
        # Reject traversal and hidden files even inside the static directory.
        candidate = Path(self.translate_path(parsed.path)).resolve()
        if not candidate.is_relative_to(PUBLIC.resolve()) or any(p.startswith(".") for p in candidate.relative_to(PUBLIC.resolve()).parts):
            return self.reply(404, {"detail": "Not found"})
        if candidate.is_dir() and candidate != PUBLIC.resolve():
            return self.reply(404, {"detail": "Not found"})
        return super().do_GET()

    def do_HEAD(self):
        # HEAD must not bypass the bridge's host/origin or path policy.
        return self.reply(405, {"detail": "GET only"})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), partial(WorkbenchHandler, directory=str(PUBLIC)))
    print(f"AegisOps workbench: http://127.0.0.1:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
