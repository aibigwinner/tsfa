import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from storage import get_or_create_player, polls, create_poll, vote_in_poll, close_poll, get_poll_results

h = html.escape


async def poll_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    if not player.get("is_admin"):
        await update.message.reply_text("❌ Нет прав администратора.")
        return

    args = context.args
    text = " ".join(args)
    parts = [p.strip() for p in text.split("|")] if "|" in text else args

    if len(parts) < 3:
        await update.message.reply_text(
            "Использование: <code>/poll &lt;вопрос&gt; | &lt;вар1&gt; | &lt;вар2&gt; | ...</code>\n\n"
            "Пример: <code>/poll Какой челлендж? | 10 побед Рэйденом | 20 побед Лин | 5 побед любым</code>",
            parse_mode="HTML",
        )
        return

    question = parts[0]
    options = parts[1:]
    if len(options) < 2:
        await update.message.reply_text("Нужно минимум 2 варианта ответа.")
        return
    if len(options) > 9:
        await update.message.reply_text("Максимум 9 вариантов.")
        return

    poll = create_poll(question, options, user.id)

    text_lines = [f"<b>📊 Голосование:</b>\n{h(poll['question'])}\n"]
    keyboard = []
    for key, label in poll["options"].items():
        text_lines.append(f"{key}. {h(label)}")
        keyboard.append([
            InlineKeyboardButton(
                f"{key}. {label}", callback_data=f"vote_{poll['id']}_{key}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton("🔒 Закрыть", callback_data=f"poll_close_{poll['id']}")
    ])

    await update.message.reply_text(
        "\n".join(text_lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def poll_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.replace("vote_", "")
    poll_id, option_key = data.rsplit("_", 1)

    success, error = vote_in_poll(poll_id, query.from_user.id, option_key)
    if not success:
        await query.answer(error, show_alert=True)
        return

    poll = polls.get(poll_id)
    if not poll:
        return

    total_votes = len(poll["votes"])
    text_lines = [f"<b>📊 Голосование:</b>\n{h(poll['question'])}\n"]
    for key, label in poll["options"].items():
        count = sum(1 for v in poll["votes"].values() if v == key)
        bar = "█" * count + "░" * max(0, total_votes - count)
        text_lines.append(f"{key}. {h(label)}\n   [{bar}] {count} голос(ов)")

    await query.edit_message_text(
        "\n".join(text_lines),
        parse_mode="HTML",
        reply_markup=query.message.reply_markup,
    )


async def poll_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    poll_id = query.data.replace("poll_close_", "")

    player = get_or_create_player(query.from_user.id)
    if not player.get("is_admin"):
        await query.answer("Только админ может закрыть голосование.", show_alert=True)
        return

    poll = close_poll(poll_id)
    if not poll:
        await query.answer("Голосование не найдено.")
        return

    results = get_poll_results(poll_id)
    total = sum(results.values()) if results else 0
    winner = max(results, key=results.get) if results else "—"

    text_lines = [
        f"<b>📊 Голосование завершено!</b>\n{h(poll['question'])}\n",
        f"<b>🏆 Победитель:</b> {winner}\n",
        "<b>Результаты:</b>",
    ]
    for label, count in results.items():
        bar = "█" * count + "░" * max(0, total - count)
        pct = f"{count * 100 // total}%" if total > 0 else "0%"
        text_lines.append(f"  {h(label)}: [{bar}] {count} ({pct})")

    await query.edit_message_text(
        "\n".join(text_lines),
        parse_mode="HTML",
    )
