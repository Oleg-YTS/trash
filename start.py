"""
Запускает бота с healthcheck сервером.
Для локальной разработки используется polling + healthcheck сервер.
Для production (Render) используется webhook + healthcheck сервер.
"""

import os
import sys
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import flask
from telebot import types

# ─── Конфигурация ───

PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
USE_POLLING = os.environ.get("USE_POLLING", "false").lower() == "true"

# ─── Логирование ───

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Импортируем бота ───

from fridge_bot import bot

# ─── Flask приложение ───

app = flask.Flask(__name__)


@app.route("/", methods=["GET", "HEAD"])
def healthcheck():
    """Healthcheck эндпоинт для Render."""
    return "OK — trash-diet bot is running", 200


@app.route("/webhook", methods=["POST"])
def webhook_handler():
    """Обрабатывает обновления от Telegram."""
    if flask.request.headers.get("content-type") == "application/json":
        json_string = flask.request.get_data().decode("utf-8")
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "", 200
    else:
        flask.abort(403)


# ─── Запуск ───

def start_flask(port: int):
    """Запускает Flask сервер в отдельном потоке (для healthcheck)."""
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def main():
    if USE_POLLING:
        # Локальная разработка — polling + healthcheck
        logger.info(f"Starting healthcheck server on port {PORT}")
        flask_thread = threading.Thread(target=start_flask, args=(PORT,), daemon=True)
        flask_thread.start()
        time.sleep(1)  # Ждём запуск Flask

        logger.info("Starting bot in POLLING mode (local development)")
        logger.info(f"Healthcheck: http://localhost:{PORT}/")
        logger.info("Bot is ready to receive updates!")
        bot.infinity_polling(timeout=30, long_polling_timeout=30)
    else:
        # Production — webhook
        if not WEBHOOK_URL:
            logger.error("WEBHOOK_URL не задан в переменных окружения!")
            logger.info("Для локальной разработки используйте USE_POLLING=true")
            sys.exit(1)

        # Удаляем старый webhook
        logger.info("Removing old webhook...")
        bot.remove_webhook()
        time.sleep(1)

        # Устанавливаем новый webhook
        logger.info(f"Setting webhook to {WEBHOOK_URL}")
        bot.set_webhook(url=WEBHOOK_URL)

        # Запускаем Flask сервер (webhook + healthcheck)
        logger.info(f"Starting Flask server on port {PORT}")
        logger.info(f"Healthcheck: http://0.0.0.0:{PORT}/")
        logger.info(f"Webhook: {WEBHOOK_URL}")
        logger.info("Bot is ready to receive updates!")

        app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
    main()
