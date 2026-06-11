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

    app = build_application()

    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
        logging.info(f"Shadow Fight Arena Bot запущен (webhook): {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=webhook_url,
        )
    else:
        logging.info("RENDER_EXTERNAL_URL не задан, переключение в polling")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
