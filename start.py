"""
Запускает healthcheck-сервер и бота одновременно.
Используется как точка входа для Render.com.
"""

import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


# ─── Healthcheck сервер ───

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, fmt, *args):
        print(f"[healthcheck] {fmt % args}", flush=True)


def start_healthcheck():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"[healthcheck] Listening on port {port}", flush=True)
    sys.stdout.flush()
    server.serve_forever()


# ─── Запуск ───

def main():
    # Запускаем healthcheck в отдельном потоке
    hc_thread = threading.Thread(target=start_healthcheck, daemon=True)
    hc_thread.start()

    # Запускаем бота в основном потоке
    print("[start] Starting fridge_bot...", flush=True)
    sys.stdout.flush()

    # Импортируем и запускаем бота
    import fridge_bot


if __name__ == "__main__":
    main()
