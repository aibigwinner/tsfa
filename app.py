import asyncio
import os
import logging
import signal

import tornado.web
import tornado.httpserver
import tornado.ioloop
from telegram import Update

from telegram.ext._utils.webhookhandler import TelegramHandler

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


def main():
    PORT = int(os.getenv("PORT", 8080))
    RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
    IS_RENDER = os.getenv("RENDER", "").lower() in ("1", "true", "yes")

    logger.info(f"RENDER={os.getenv('RENDER', '—')} | "
                f"RENDER_EXTERNAL_URL={RENDER_EXTERNAL_URL or '—'} | "
                f"PORT={PORT}")

    app = build_application()

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

        # Build Tornado app with health + webhook routes
        shared_objects = {
            "bot": app.bot,
            "update_queue": app.update_queue,
            "secret_token": None,
        }
        handlers = [
            (r"/health/?", HealthHandler),
            (rf"/{BOT_TOKEN}/?", TelegramHandler, shared_objects),
        ]
        tornado_app = tornado.web.Application(handlers)

        async def startup():
            await app.initialize()
            await app.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Старый webhook сброшен")
            await app.start()

            server = tornado.httpserver.HTTPServer(tornado_app)
            server.listen(PORT, address="0.0.0.0")
            logger.info(f"Сервер слушает порт {PORT}")

            await app.bot.set_webhook(url=webhook_url)
            logger.info(f"Webhook установлен: {webhook_url}")

        async def shutdown():
            logger.info("Остановка...")
            await app.stop()
            await app.shutdown()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(startup())

            for sig in (signal.SIGTERM, signal.SIGINT):
                try:
                    loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
                except NotImplementedError:
                    pass

            loop.run_forever()
        except KeyboardInterrupt:
            loop.run_until_complete(shutdown())
        finally:
            loop.close()
    else:
        logger.info("Polling mode (локально)")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
