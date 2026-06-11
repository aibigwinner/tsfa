import html

from telegram import Update
from telegram.ext import ContextTypes

from storage import get_or_create_player

h = html.escape


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_player(user.id, user.username, user.first_name)

    text = (
        f"👋 Добро пожаловать в <b>Shadow Fight 4: Arena — Бот для турниров!</b>\n\n"
        f"🎮 <b>Команды:</b>\n"
        f"<code>/help</code> — всё команды\n"
        f"<code>/battle</code> — создать или найти бой\n"
        f"<code>/tournament</code> — список турниров\n"
        f"<code>/profile</code> — мой профиль\n"
        f"<code>/leaderboard</code> — топ игроков\n\n"
        f"Создавай бои, участвуй в турнирах и становись лучшим! ⚔️"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)

    lines = [
        "🎮 <b>Доступные команды:</b>\n",
        "<b>Для всех:</b>",
        "<code>/start</code> — приветствие",
        "<code>/help</code> — это сообщение",
        "<code>/profile</code> — мой профиль и статистика",
        "<code>/leaderboard</code> — рейтинг игроков",
        "<code>/battle</code> — создать или найти бой",
        "<code>/battles</code> — список активных боёв",
        "<code>/tournament</code> — список турниров",
        "<code>/achievements</code> — достижения",
        "<code>/backup</code> — резервная копия (админ)",
        "",
        "<b>Для администраторов:</b>",
        "<code>/announce &lt;текст&gt;</code> — сделать объявление",
        "<code>/challenge</code> — создать челлендж/ивент",
        "<code>/tournament_new</code> — создать новый турнир",
        "<code>/ban &lt;user_id&gt;</code> — забанить игрока",
        "<code>/unban &lt;user_id&gt;</code> — разбанить",
    ]

    text = "\n".join(lines) if player.get("is_admin") else "\n".join(lines[:-7])

    await update.message.reply_text(text, parse_mode="HTML")
