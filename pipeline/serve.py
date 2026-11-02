"""Local preview that behaves like Cloudflare Pages: applies site/_headers and serves 404.html.

    uv run python pipeline/serve.py [port]
"""

import fnmatch
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"


def parse_headers():
    rules, current = [], None
    for line in (SITE / "_headers").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")):
            current = (line.strip(), [])
            rules.append(current)
        elif current:
            name, _, value = line.strip().partition(":")
            current[1].append((name.strip(), value.strip()))
    return rules


class Handler(SimpleHTTPRequestHandler):
    rules = parse_headers()

    def end_headers(self):
        path = self.path.split("?")[0]
        for pattern, headers in self.rules:
            if fnmatch.fnmatch(path, pattern):
                for name, value in headers:
                    self.send_header(name, value)
        super().end_headers()

    def send_error(self, code, message=None, explain=None):
        if code == 404 and (SITE / "404.html").exists():
            body = (SITE / "404.html").read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().send_error(code, message, explain)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"serving {SITE} on http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=str(SITE))).serve_forever()
