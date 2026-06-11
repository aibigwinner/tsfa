import os
import logging
from telegram import Update
from telegram.ext import Application

from main import build_application
from config import BOT_TOKEN

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def main():
    PORT = int(os.getenv("PORT", 8080))
    RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
    IS_RENDER = os.getenv("RENDER") == "1"

    app = build_application()

    if IS_RENDER and RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL.strip('/')}/{BOT_TOKEN}"
        logging.info(f"🌐 Webhook mode: {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=webhook_url,
        )
    elif IS_RENDER:
        logging.warning("⚠️ RENDER_EXTERNAL_URL не найден. Укажи в Variables → RENDER_EXTERNAL_URL")
        logging.info("🔄 Запуск в polling mode...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    else:
        logging.info("🔄 Polling mode (локальный запуск)")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
