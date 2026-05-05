from __future__ import annotations

from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
import webbrowser

from trading_lab.portfolio.gui_forms import apply_form_action
from trading_lab.portfolio.gui_render import render_status_page


def run_gui(host: str = "127.0.0.1", port: int = 8765) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            query = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            risk_mode = query.get("risk_mode", ["conservative"])[-1]
            active_tab = query.get("tab", ["daily"])[-1]
            body = render_status_page(risk_mode=risk_mode, active_tab=active_tab).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            fields = {key: values[-1] for key, values in parse_qs(raw).items()}
            try:
                apply_form_action(self.path, fields)
                self.send_response(303)
                self.send_header("Location", "/")
                self.end_headers()
            except Exception as exc:
                body = escape(str(exc)).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{server.server_port}/"
    print(f"Local-only portfolio GUI: {url}")
    print("Press Ctrl+C to stop.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping portfolio GUI.")
    finally:
        server.server_close()
