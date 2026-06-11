from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from storage import get_or_create_player, players, create_challenge, create_tournament


async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    if not player.get("is_admin"):
        await update.message.reply_text("❌ Нет прав администратора.")
        return

    text = " ".join(context.args)
    if not text:
        await update.message.reply_text(
            "Использование: `/announce <текст>`", parse_mode=ParseMode.MARKDOWN
        )
        return

    await update.message.reply_text(
        f"📢 **Объявление от администрации:**\n\n{text}",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        await update.message.delete()
    except Exception:
        pass


async def challenge_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    if not player.get("is_admin"):
        await update.message.reply_text("❌ Нет прав администратора.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Использование: `/challenge <название> | <описание> | <цель>`\n\n"
            "Пример: `/challenge 10 побед Рэйденом | Одержи 10 побед за Рэйдена | 10`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    full = " ".join(args)
    parts = [p.strip() for p in full.split("|")]
    title = parts[0] if len(parts) > 0 else "Челлендж"
    description = parts[1] if len(parts) > 1 else ""
    target = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 10

    challenge = create_challenge(title, description, user.id, target)
    await update.message.reply_text(
        f"🔥 **Новый челлендж!**\n\n"
        f"**{challenge['title']}**\n"
        f"{challenge['description']}\n\n"
        f"Цель: {challenge['target_count']} очков\n"
        f"Статус: Активен\n\n"
        f"Участвуйте и побеждайте! ⚔️",
        parse_mode=ParseMode.MARKDOWN,
    )


async def tournament_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    if not player.get("is_admin"):
        await update.message.reply_text("❌ Нет прав администратора.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Использование: `/tournament_new <название> [макс. игроков]`\n\n"
            "Пример: `/tournament_new Кубок Сезона 8`\n"
            "Пример: `/tournament_new Мини-турнир 4` — на 4 игроков",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    name_parts = []
    max_players = 8
    for arg in args:
        if arg.isdigit() and len(args) > 1:
            max_players = int(arg)
        else:
            name_parts.append(arg)

    name = " ".join(name_parts) if name_parts else "Турнир"
    t = create_tournament(name, user.id, max_players)

    await update.message.reply_text(
        f"✅ **Турнир создан!**\n\n"
        f"Название: {t['name']}\n"
        f"Макс. игроков: {t['max_players']}\n"
        f"ID: `{t['id']}`\n\n"
        f"Начать можно: `/tournament_start {t['id']}`\n"
        f"Провести раунд: `/tadvance {t['id']} <номер матча> <id победителя>`",
        parse_mode=ParseMode.MARKDOWN,
    )


async def ban_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    if not player.get("is_admin"):
        await update.message.reply_text("❌ Нет прав.")
        return

    if not context.args:
        await update.message.reply_text("Укажи ID: `/ban <id>`", parse_mode=ParseMode.MARKDOWN)
        return

    target_id = context.args[0]
    target = players.get(target_id)
    if not target:
        await update.message.reply_text("❌ Игрок не найден.")
        return

    target["is_banned"] = True
    players.set(target_id, target)
    await update.message.reply_text(f"✅ Игрок {target.get('first_name', target_id)} забанен.")


async def unban_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    if not player.get("is_admin"):
        await update.message.reply_text("❌ Нет прав.")
        return

    if not context.args:
        await update.message.reply_text("Укажи ID: `/unban <id>`", parse_mode=ParseMode.MARKDOWN)
        return

    target_id = context.args[0]
    target = players.get(target_id)
    if not target:
        await update.message.reply_text("❌ Игрок не найден.")
        return

    target["is_banned"] = False
    players.set(target_id, target)
    await update.message.reply_text(f"✅ Игрок {target.get('first_name', target_id)} разбанен.")
