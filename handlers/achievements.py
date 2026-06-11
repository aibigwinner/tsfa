from telegram import Update
from telegram.ext import ContextTypes

from storage import get_or_create_player, award_achievement, get_player

ACHIEVEMENTS = [
    {
        "id": "first_win",
        "name": "Первая победа",
        "desc": "Одержать первую победу",
        "icon": "🏆",
        "check": lambda p: p.get("wins", 0) >= 1,
    },
    {
        "id": "ten_wins",
        "name": "Ветеран",
        "desc": "10 побед",
        "icon": "🎖️",
        "check": lambda p: p.get("wins", 0) >= 10,
    },
    {
        "id": "fifty_battles",
        "name": "Боец",
        "desc": "50 боёв",
        "icon": "⚔️",
        "check": lambda p: p.get("total_battles", 0) >= 50,
    },
    {
        "id": "streak_5",
        "name": "На грани",
        "desc": "5 побед подряд",
        "icon": "🔥",
        "check": lambda p: p.get("max_streak", 0) >= 5,
    },
    {
        "id": "streak_10",
        "name": "Неудержимый",
        "desc": "10 побед подряд",
        "icon": "💥",
        "check": lambda p: p.get("max_streak", 0) >= 10,
    },
    {
        "id": "tournament_winner",
        "name": "Чемпион",
        "desc": "Выиграть турнир",
        "icon": "👑",
        "check": lambda p: p.get("tournament_wins", 0) >= 1,
    },
    {
        "id": "character_master",
        "name": "Мастер персонажа",
        "desc": "10 побед одним персонажем",
        "icon": "🎯",
        "check": lambda p: any(
            c.get("wins", 0) >= 10
            for c in p.get("characters", {}).values()
        ),
    },
    {
        "id": "hundred_battles",
        "name": "Легенда",
        "desc": "100 боёв",
        "icon": "💎",
        "check": lambda p: p.get("total_battles", 0) >= 100,
    },
]


def check_and_award(user_id):
    player = get_player(user_id)
    if not player:
        return []
    newly_earned = []
    for ach in ACHIEVEMENTS:
        try:
            if ach["check"](player):
                if award_achievement(user_id, ach["id"]):
                    newly_earned.append(ach)
        except Exception:
            pass
    return newly_earned


async def achievements_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    earned = set(player.get("achievements", []))

    lines = ["**🎖️ Достижения:**\n"]
    for ach in ACHIEVEMENTS:
        mark = "✅" if ach["id"] in earned else "⬜"
        lines.append(f"{mark} {ach['icon']} **{ach['name']}** — {ach['desc']}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
