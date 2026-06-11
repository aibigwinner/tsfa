import html

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from storage import get_or_create_player, players, create_challenge, create_tournament
from database import get_db_path

h = html.escape


async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    if not player.get("is_admin"):
        await update.message.reply_text("❌ Нет прав администратора.")
        return

    text = " ".join(context.args)
    if not text:
        await update.message.reply_text(
            'Использование: <code>/announce &lt;текст&gt;</code>',
            parse_mode=ParseMode.HTML,
        )
        return

    await update.message.reply_text(
        f"📢 <b>Объявление от администрации:</b>\n\n{h(text)}",
        parse_mode=ParseMode.HTML,
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
            "Использование: <code>/challenge &lt;название&gt; | &lt;описание&gt; | &lt;цель&gt;</code>\n\n"
            "Пример: <code>/challenge 10 побед Рэйденом | Одержи 10 побед за Рэйдена | 10</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    full = " ".join(args)
    parts = [p.strip() for p in full.split("|")]
    title = parts[0] if len(parts) > 0 else "Челлендж"
    description = parts[1] if len(parts) > 1 else ""
    target = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 10

    challenge = create_challenge(title, description, user.id, target)
    await update.message.reply_text(
        f"🔥 <b>Новый челлендж!</b>\n\n"
        f"<b>{h(challenge['title'])}</b>\n"
        f"{h(challenge['description'])}\n\n"
        f"Цель: {challenge['target_count']} очков\n"
        f"Статус: Активен\n\n"
        f"Участвуйте и побеждайте! ⚔️",
        parse_mode=ParseMode.HTML,
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
            "Использование: <code>/tournament_new &lt;название&gt; [макс. игроков]</code>\n\n"
            "Пример: <code>/tournament_new Кубок Сезона 8</code>\n"
            "Пример: <code>/tournament_new Мини-турнир 4</code> — на 4 игроков",
            parse_mode=ParseMode.HTML,
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
        f"✅ <b>Турнир создан!</b>\n\n"
        f"Название: {h(t['name'])}\n"
        f"Макс. игроков: {t['max_players']}\n"
        f"ID: <code>{t['id']}</code>\n\n"
        f"Начать можно: <code>/tournament_start {t['id']}</code>\n"
        f"Провести раунд: <code>/tadvance {t['id']} &lt;номер матча&gt; &lt;id победителя&gt;</code>",
        parse_mode=ParseMode.HTML,
    )

    try:
        await update.message.reply_text(
            f"🏆 <b>Новый турнир!</b>\n\n"
            f"<b>{h(t['name'])}</b>\n"
            f"Макс. участников: {t['max_players']}\n\n"
            f"Записаться: <code>/tournament</code>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def ban_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    if not player.get("is_admin"):
        await update.message.reply_text("❌ Нет прав.")
        return

    if not context.args:
        await update.message.reply_text(
            "Укажи ID: <code>/ban &lt;id&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    target_id = context.args[0]
    target = players.get(target_id)
    if not target:
        await update.message.reply_text("❌ Игрок не найден.")
        return

    target["is_banned"] = True
    players.set(target_id, target)
    await update.message.reply_text(
        f"✅ Игрок {h(target.get('first_name', target_id))} забанен.",
    )


async def unban_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    if not player.get("is_admin"):
        await update.message.reply_text("❌ Нет прав.")
        return

    if not context.args:
        await update.message.reply_text(
            "Укажи ID: <code>/unban &lt;id&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    target_id = context.args[0]
    target = players.get(target_id)
    if not target:
        await update.message.reply_text("❌ Игрок не найден.")
        return

    target["is_banned"] = False
    players.set(target_id, target)
    await update.message.reply_text(
        f"✅ Игрок {h(target.get('first_name', target_id))} разбанен.",
    )


async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    if not player.get("is_admin"):
        await update.message.reply_text("❌ Нет прав.")
        return

    db_path = get_db_path()
    if not db_path.exists():
        await update.message.reply_text("❌ База данных не найдена.")
        return

    await update.message.reply_document(
        document=open(str(db_path), "rb"),
        filename="tsfa_backup.db",
        caption="✅ Резервная копия базы данных.",
    )


async def restore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    if not player.get("is_admin"):
        await update.message.reply_text("❌ Нет прав.")
        return

    context.user_data["awaiting_restore"] = True
    await update.message.reply_text(
        "📤 Отправь <code>.db</code> файл резервной копии.",
        parse_mode=ParseMode.HTML,
    )


async def restore_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_restore"):
        return

    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    if not player.get("is_admin"):
        return

    doc = update.message.document
    if not doc.file_name or not doc.file_name.endswith(".db"):
        await update.message.reply_text("❌ Ожидался файл с расширением <code>.db</code>.", parse_mode=ParseMode.HTML)
        context.user_data.pop("awaiting_restore", None)
        return

    file = await doc.get_file()
    db_path = get_db_path()
    await file.download_to_drive(custom_path=str(db_path))
    context.user_data.pop("awaiting_restore", None)
    await update.message.reply_text("✅ База данных восстановлена из резервной копии.")
