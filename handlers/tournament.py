import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from storage import (
    tournaments, get_player, get_or_create_player, create_tournament,
    register_for_tournament, generate_bracket, advance_round,
)

from handlers.notifications import notify_tournament_start

h = html.escape


async def tournament_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_tournaments = tournaments.all()
    if not all_tournaments:
        await update.message.reply_text(
            "😕 Пока нет турниров. Админ может создать: <code>/tournament_new</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    lines = ["<b>🏆 Турниры:</b>\n"]
    keyboard = []
    for tid, t in list(all_tournaments.items())[:5]:
        status = t["status"]
        players_count = len(t.get("players", []))
        status_emoji = {"registration": "📝", "ongoing": "⚔️", "completed": "🏆"}.get(status, "❓")
        lines.append(
            f"{status_emoji} <b>{h(t['name'])}</b> — {players_count}/{t['max_players']} "
            f"| {status}"
        )
        if status == "registration":
            keyboard.append([
                InlineKeyboardButton(
                    f"📝 Записаться: {t['name']}", callback_data=f"treg_{tid}"
                )
            ])
        elif status in ("ongoing", "completed"):
            keyboard.append([
                InlineKeyboardButton(
                    f"📋 Сетка: {t['name']}", callback_data=f"tbracket_{tid}"
                )
            ])

    if keyboard:
        keyboard.append([InlineKeyboardButton("🏆 Создать турнир", callback_data="tournament_new")])
        await update.message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def tournament_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tid = query.data.replace("treg_", "")
    result, error = register_for_tournament(tid, query.from_user.id)
    if error:
        await query.edit_message_text(f"❌ {error}")
    else:
        t = tournaments.get(tid)
        await query.edit_message_text(
            f"✅ <b>Ты зарегистрирован!</b>\n"
            f"<code>{h(t['name'])}</code>\n"
            f"Игроков: {len(t['players'])}/{t['max_players']}\n\n"
            f"Ожидай начала!",
            parse_mode=ParseMode.HTML,
        )


async def tournament_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    if not player.get("is_admin"):
        await update.message.reply_text("❌ Нет прав.")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "Использование: <code>/tournament_start &lt;id турнира&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    tid = args[0]
    result, error = generate_bracket(tid)
    if error:
        await update.message.reply_text(f"❌ {error}")
        return

    await notify_tournament_start(context, result)

    t = tournaments.get(tid)
    try:
        await update.message.reply_text(
            f"🏆 <b>Турнир начался!</b>\n\n"
            f"<b>{h(t['name'])}</b> — {len(t['players'])} участников\n"
            f"Сетка готова, бои пошли!",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    text = format_bracket(result, result["current_round"])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def tournament_advance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_or_create_player(user.id, user.username, user.first_name)
    if not player.get("is_admin"):
        await update.message.reply_text("❌ Нет прав.")
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "Использование: <code>/tadvance &lt;id турнира&gt; &lt;номер матча&gt; &lt;id победителя&gt;</code>\n"
            "Номер матча начинается с 0.\n"
            "Пример: <code>/tadvance tournament_123456789 0 987654321</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    tid, match_idx, winner_id = args[0], int(args[1]), args[2]
    result, msg = advance_round(tid, match_idx, winner_id)
    if not result:
        await update.message.reply_text(f"❌ {msg}")
        return

    text = format_bracket(result, result["current_round"])
    text = f"<b>{msg}</b>\n\n{text}"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def tournament_view_bracket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tid = query.data.replace("tbracket_", "")
    t = tournaments.get(tid)
    if not t:
        await query.edit_message_text("❌ Турнир не найден.")
        return

    text = format_bracket(t, t["current_round"])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML)


def format_bracket(t, current_round):
    lines = [f"<b>🏆 {h(t['name'])}</b> — {t['status']}\n"]
    players = t.get("players", [])
    lines.append(f"Участники: {len(players)}\n")

    bracket = t.get("bracket", [])
    if not bracket:
        return "\n".join(lines)

    for round_idx, round_matches in enumerate(bracket, 1):
        round_label = "⚔️" if round_idx == current_round else ("✅" if round_idx < current_round else "⏳")
        lines.append(f"\n{round_label} <b>Раунд {round_idx}:</b>")
        for m_idx, match in enumerate(round_matches):
            p1 = p2 = "—"
            w_icon = ""
            if isinstance(match.get("p1"), dict):
                p1 = h(match["p1"].get("first_name", "???"))
                if match.get("bye"):
                    w_icon = " 🆓"
            elif match.get("p1"):
                p1 = h(match["p1"])
            if isinstance(match.get("p2"), dict):
                p2 = h(match["p2"].get("first_name", "???"))
            elif match.get("p2"):
                p2 = h(match["p2"])
            elif match.get("bye"):
                p2 = "bye"

            if match.get("winner"):
                if isinstance(match["winner"], dict):
                    wn = h(match["winner"].get("first_name", "???"))
                else:
                    wn = h(match["winner"])
                w_icon = f" 🏆 {wn}"

            lines.append(f"  {m_idx + 1}. {p1} vs {p2}{w_icon}")

    if t["status"] == "completed":
        last_match = bracket[-1][0] if bracket else {}
        if last_match.get("winner"):
            wn = h(last_match["winner"].get("first_name", "???")) if isinstance(last_match["winner"], dict) else h(last_match["winner"])
            lines.append(f"\n👑 <b>Чемпион: {wn}</b>")

    return "\n".join(lines)


async def tournament_bracket_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = " ".join(context.args) if context.args else None
    if not tid:
        await update.message.reply_text(
            "Использование: <code>/bracket &lt;id турнира&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    t = tournaments.get(tid)
    if not t:
        await update.message.reply_text("❌ Турнир не найден.")
        return
    text = format_bracket(t, t["current_round"])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
