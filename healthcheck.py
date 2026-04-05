"""
Простой healthcheck сервер для Render.com
Render требует HTTP-эндпоинт для проверки здоровья сервиса.
"""

import os
from http.server import HTTPServer, BaseHTTPRequestHandler


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK — trash-diet bot is running")

    def log_message(self, format, *args):
        pass  # Тихий режим


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"🏥 Healthcheck сервер запущен на порту {port}")
    server.serve_forever()
