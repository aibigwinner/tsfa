from telegram import Update
from telegram.ext import ContextTypes

from storage import get_or_create_player


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_player(user.id, user.username, user.first_name)

    text = (
        f"👋 Добро пожаловать в **Shadow Fight 4: Arena — Бот для турниров!**\n\n"
        f"🎮 **Команды:**\n"
        f"`/help` — всё команды\n"
        f"`/battle` — создать или найти бой\n"
        f"`/tournament` — список турниров\n"
        f"`/profile` — мой профиль\n"
        f"`/leaderboard` — топ игроков\n\n"
        f"Создавай бои, участвуй в турнирах и становись лучшим! ⚔️"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)

    lines = [
        "**🎮 Доступные команды:**\n",
        "**Для всех:**",
        "`/start` — приветствие",
        "`/help` — это сообщение",
        "`/profile` — мой профиль и статистика",
        "`/leaderboard` — рейтинг игроков",
        "`/battle` — создать или найти бой",
        "`/battles` — список активных боёв",
        "`/tournament` — список турниров",
        "",
        "**Для администраторов:**",
        "`/announce <текст>` — сделать объявление",
        "`/challenge` — создать челлендж/ивент",
        "`/tournament_new` — создать новый турнир",
        "`/ban <user_id>` — забанить игрока",
        "`/unban <user_id>` — разбанить",
    ]

    if player.get("is_admin"):
        text = "\n".join(lines)
    else:
        text = "\n".join(lines[:-6])

    await update.message.reply_text(text, parse_mode="Markdown")
