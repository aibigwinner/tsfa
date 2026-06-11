import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from storage import get_or_create_player, get_player, players

h = html.escape

POPULAR_CHARACTERS = [
    "Рэйден", "Лин", "Тень", "Джун", "Император", "Кибо",
    "Джет", "Линкс", "Файргард", "Хонг-Джу", "Сарж",
    "Адзума", "Сёгун", "Юкка", "Маркус", "Кейт",
    "Король Обезьян", "Иту", "Кобра", "Сяндэр", "Цзу",
]


async def choose_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    rows = []
    for i in range(0, len(POPULAR_CHARACTERS), 3):
        chunk = POPULAR_CHARACTERS[i:i + 3]
        rows.append([
            InlineKeyboardButton(c, callback_data=f"char_{c}")
            for c in chunk
        ])
    rows.append([InlineKeyboardButton("✏️ Свой вариант", callback_data="char_custom")])
    rows.append([InlineKeyboardButton("◀ Назад", callback_data="char_skip")])

    await query.edit_message_text(
        "<b>Выбери своего персонажа:</b>\n(или нажми «Пропустить»)",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def character_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    char = query.data.replace("char_", "")
    if char == "skip":
        context.user_data["character"] = None
        await query.edit_message_text("✅ Персонаж не указан.")
        return
    context.user_data["character"] = char
    await query.edit_message_text(f"✅ Персонаж: <b>{h(char)}</b>", parse_mode="HTML")


async def character_stats_text(user_id):
    player = get_player(user_id)
    if not player:
        return ""
    chars = player.get("characters", {})
    if not chars:
        return ""

    lines = ["\n<b>🎯 Статистика по персонажам:</b>"]
    sorted_chars = sorted(
        chars.values(), key=lambda c: c.get("total", 0), reverse=True
    )[:10]
    for c in sorted_chars:
        name = h(c.get("name", "???"))
        w = c.get("wins", 0)
        l = c.get("losses", 0)
        t = c.get("total", 0)
        wr = f"{w * 100 // t}%" if t > 0 else "0%"
        lines.append(f"  {name}: {w}W/{l}L ({wr})")
    return "\n".join(lines)
