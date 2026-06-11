from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from storage import get_or_create_player, get_player, battles, players as players_storage
from handlers.achievements import ACHIEVEMENTS
from handlers.characters import character_stats_text


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    wins = player.get("wins", 0)
    losses = player.get("losses", 0)
    total = player.get("total_battles", 0)
    wr = f"{wins * 100 // total}%" if total > 0 else "0%"
    streak = player.get("current_streak", 0)
    ach_count = len(player.get("achievements", []))

    text = (
        f"**Профиль игрока** 🆔\n"
        f"Имя: {player.get('first_name', 'Игрок')}\n"
        f"Username: @{player.get('username', '—')}\n"
        f"Рейтинг: {player.get('rating', 1000)} ⭐\n"
        f"Победы: {wins} | Поражения: {losses} | WR: {wr}\n"
        f"Всего боёв: {total} ⚔️\n"
        f"Текущая серия: {streak} 🔥\n"
        f"Достижений: {ach_count} 🎖️\n"
        f"Роль: {'Админ' if player.get('is_admin') else 'Игрок'}"
    )

    char_stats = await character_stats_text(user.id)
    if char_stats:
        text += char_stats

    all_battles = battles.all()
    user_id = str(user.id)
    active_count = sum(
        1 for b in all_battles.values()
        if b["status"] in ("waiting", "active")
        and (b["creator_id"] == user_id or b.get("opponent_id") == user_id)
    )
    if active_count:
        text += f"\nАктивных боёв: {active_count}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Топ игроков", callback_data="leaderboard"),
         InlineKeyboardButton("🎖️ Достижения", callback_data="achievements")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_players = [
        p for p in players_storage.all().values()
        if not p.get("is_banned")
    ]
    sorted_players = sorted(
        all_players, key=lambda p: p.get("rating", 1000), reverse=True
    )[:20]

    lines = ["**📊 Топ игроков:**\n"]
    for i, p in enumerate(sorted_players, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        wr = f"{p.get('wins', 0) * 100 // max(p.get('total_battles', 0), 1)}%"
        lines.append(
            f"{medal} {p.get('first_name', 'Игрок')} "
            f"— {p.get('rating', 1000)} ⭐ "
            f"(W:{p.get('wins', 0)} / L:{p.get('losses', 0)} / {wr})"
        )

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    all_players = [
        p for p in players_storage.all().values()
        if not p.get("is_banned")
    ]
    sorted_players = sorted(
        all_players, key=lambda p: p.get("rating", 1000), reverse=True
    )[:20]

    lines = ["**📊 Топ игроков:**\n"]
    for i, p in enumerate(sorted_players, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        wr = f"{p.get('wins', 0) * 100 // max(p.get('total_battles', 0), 1)}%"
        lines.append(
            f"{medal} {p.get('first_name', 'Игрок')} "
            f"— {p.get('rating', 1000)} ⭐ "
            f"(W:{p.get('wins', 0)} / L:{p.get('losses', 0)} / {wr})"
        )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎖️ Мои достижения", callback_data="achievements")],
    ])
    await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def profile_achievements_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.achievements import ACHIEVEMENTS
    query = update.callback_query
    await query.answer()
    user = query.from_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    earned = set(player.get("achievements", []))

    lines = ["**🎖️ Достижения:**\n"]
    for ach in ACHIEVEMENTS:
        mark = "✅" if ach["id"] in earned else "⬜"
        lines.append(f"{mark} {ach['icon']} **{ach['name']}** — {ach['desc']}")

    await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
