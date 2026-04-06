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
        
        # Передаём обновление во все возможные обработчики
        try:
            if update.message:
                bot.process_new_messages([update.message])
            if update.edited_message:
                bot.process_new_edited_messages([update.edited_message])
            if update.channel_post:
                bot.process_new_channel_posts([update.channel_post])
            if update.callback_query:
                bot.process_new_callback_queries([update.callback_query])
            if update.inline_query:
                bot.process_new_inline_queries([update.inline_query])
            if update.chosen_inline_result:
                bot.process_new_chosen_inline_results([update.chosen_inline_result])
            if update.shipping_query:
                bot.process_new_shipping_queries([update.shipping_query])
            if update.pre_checkout_query:
                bot.process_new_pre_checkout_queries([update.pre_checkout_query])
            if update.my_chat_member:
                bot.process_new_my_chat_members([update.my_chat_member])
            if update.chat_member:
                bot.process_new_chat_members([update.chat_member])
        except Exception as e:
            logger.error(f"Error processing update: {e}", exc_info=True)
        
        return "", 200
    else:
        flask.abort(403)


# ─── Инициализация webhook (для production) ───

if not USE_POLLING and WEBHOOK_URL:
    # При деплое на Render gunicorn импортирует этот модуль,
    # поэтому настройка webhook здесь, а не в main()
    logger.info("Production mode: setting up webhook...")
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")


# ─── Запуск (для локальной разработки) ───

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
        # Production — webhook уже настроен выше
        logger.info(f"Starting Flask server on port {PORT}")
        logger.info(f"Healthcheck: http://0.0.0.0:{PORT}/")
        logger.info(f"Webhook: {WEBHOOK_URL}")
        logger.info("Bot is ready to receive updates!")
        app.run(host="0.0.0.0", port=PORT, debug=False)


def start_flask(port: int):
    """Запускает Flask сервер в отдельном потоке (для healthcheck)."""
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
