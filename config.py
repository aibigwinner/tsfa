import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не указан в .env файле")

ADMIN_IDS = [
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]

BOT_USERNAME = "ShadowFightArenaBot"

BATTLE_TYPES = {
    "friendly": "Дружеский бой",
    "ranked": "Рейтинговый бой",
    "tournament": "Турнирный бой",
}

TOURNAMENT_STATUSES = {
    "registration": "Регистрация",
    "ongoing": "Идёт",
    "completed": "Завершён",
}
