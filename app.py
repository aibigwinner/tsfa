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

logger = logging.getLogger(__name__)


def main():
    PORT = int(os.getenv("PORT", 8080))
    RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
    IS_RENDER = os.getenv("RENDER") == "1"

    app = build_application()

    if IS_RENDER:
        if not RENDER_EXTERNAL_URL:
            service_name = os.getenv("RENDER_SERVICE_NAME", "")
            if service_name:
                RENDER_EXTERNAL_URL = f"https://{service_name}.onrender.com"
            else:
                logger.warning(
                    "⚠️ RENDER_EXTERNAL_URL не найден. "
                    "Добавь его вручную в Render Dashboard → Environment Variables:\n"
                    "  RENDER_EXTERNAL_URL = https://<твой-сервис>.onrender.com"
                )
                RENDER_EXTERNAL_URL = f"http://0.0.0.0:{PORT}"

        webhook_url = f"{RENDER_EXTERNAL_URL.strip('/')}/{BOT_TOKEN}"
        logger.info(f"🌐 Webhook: {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=webhook_url,
        )
    else:
        logger.info("🔄 Polling mode (локально)")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
