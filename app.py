import os
import logging

import tornado.web
from telegram import Update
from telegram.ext import Application
from telegram.ext._utils.webhookhandler import WebhookAppClass

from main import build_application
from config import BOT_TOKEN

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


class HealthHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_status(200)
        self.write("OK")
        self.finish()


_original_init = WebhookAppClass.__init__


def _patched_init(self, webhook_path, bot, update_queue, secret_token=None):
    _original_init(self, webhook_path, bot, update_queue, secret_token)
    self.handlers.insert(0, (r"/health/?", HealthHandler))


WebhookAppClass.__init__ = _patched_init


async def clear_webhook(app: Application):
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Старый webhook сброшен")


def main():
    PORT = int(os.getenv("PORT", 8080))
    RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
    IS_RENDER = os.getenv("RENDER", "").lower() in ("1", "true", "yes")

    logger.info(f"RENDER={os.getenv('RENDER', '—')} | "
                f"RENDER_EXTERNAL_URL={RENDER_EXTERNAL_URL or '—'} | "
                f"PORT={PORT}")

    app = build_application(post_init=clear_webhook)

    if IS_RENDER:
        if not RENDER_EXTERNAL_URL:
            logger.warning(
                "RENDER_EXTERNAL_URL не задан. "
                "Добавь в Render Dashboard → Environment → "
                "RENDER_EXTERNAL_URL = https://<имя>.onrender.com"
            )
            RENDER_EXTERNAL_URL = f"http://0.0.0.0:{PORT}"

        webhook_url = f"{RENDER_EXTERNAL_URL.strip('/')}/{BOT_TOKEN}"
        logger.info(f"Webhook mode: {webhook_url}")

        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=webhook_url,
        )
    else:
        logger.info("Polling mode (локально)")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
