import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from storage import (
    get_or_create_player, get_player, battles, create_battle,
    join_battle, add_screenshot, set_battle_character,
    complete_battle, cancel_battle,
)
from handlers.achievements import check_and_award
from handlers.notifications import (
    notify_battle_created, notify_battle_joined, notify_achievement,
)
from handlers.characters import POPULAR_CHARACTERS

h = html.escape


async def battle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)

    own_waiting = sum(
        1 for b in battles.all().values()
        if b["creator_id"] == user_id and b["status"] == "waiting"
    )
    own_active = sum(
        1 for b in battles.all().values()
        if (b["creator_id"] == user_id or b.get("opponent_id") == user_id)
        and b["status"] == "active"
    )

    status_line = ""
    if own_waiting or own_active:
        status_line = f"\n📋 У тебя: {own_waiting} ожидают, {own_active} в бою"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Создать бой", callback_data="battle_create")],
        [InlineKeyboardButton("🔍 Найти бой", callback_data="battle_list")],
        [InlineKeyboardButton("📸 Загрузить скриншот", callback_data="battle_screenshot")],
        [InlineKeyboardButton("✅ Завершить бой", callback_data="battle_complete")],
        [InlineKeyboardButton("❌ Отменить бой", callback_data="battle_cancel")],
    ])
    text = f"<b>🎮 Управление боями:</b>{status_line}\n\nВыбери действие:"

    if update.callback_query:
        q = update.callback_query
        owner = context.user_data.get("menu_owner")
        if owner and owner != q.from_user.id:
            await q.answer("⛔ Это меню вызвано другим игроком.", show_alert=True)
            return
        await q.answer()
        await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        context.user_data["menu_owner"] = user.id
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def battle_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    owner = context.user_data.get("menu_owner")
    if owner and owner != query.from_user.id:
        await query.answer("⛔ Это меню вызвано другим игроком.", show_alert=True)
        return

    for k in list(context.user_data.keys()):
        if k.startswith("battle_") or k in ("battle_step", "character"):
            del context.user_data[k]

    context.user_data["battle_step"] = "awaiting_game_id"
    context.user_data["owner_id"] = query.from_user.id

    await query.edit_message_text(
        "Введи <b>Game ID</b> из игры:\n"
        "Отправь ID в ответном сообщении.",
        parse_mode=ParseMode.HTML,
    )


async def battle_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    step = context.user_data.get("battle_step")

    if not step:
        return

    owner = context.user_data.get("owner_id")
    if owner and owner != user.id:
        return

    if step == "awaiting_game_id":
        context.user_data["battle_game_id"] = update.message.text.strip()
        context.user_data["battle_step"] = "awaiting_type"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤝 Дружеский", callback_data="type_friendly")],
            [InlineKeyboardButton("🏆 Рейтинговый", callback_data="type_ranked")],
        ])
        await update.message.reply_text("Выбери тип боя:", reply_markup=keyboard)

    elif step == "awaiting_screenshot_battle_id":
        await update.message.reply_text(
            "❌ Отправь <b>изображение</b> (скриншот), а не текст.",
            parse_mode=ParseMode.HTML,
        )

    elif step == "awaiting_character_name":
        char = update.message.text.strip()
        context.user_data.pop("battle_step", None)
        await _finish_battle_creation(update, context, char)

    elif step == "awaiting_opponent_character":
        char = update.message.text.strip()
        battle_id = context.user_data.get("opp_char_battle_id")
        if battle_id:
            set_battle_character(battle_id, user.id, char)
        context.user_data.pop("battle_step", None)
        context.user_data.pop("opp_char_battle_id", None)
        await update.message.reply_text(f"✅ Персонаж: <b>{h(char)}</b>. Удачного боя! ⚔️",
                                        parse_mode=ParseMode.HTML)

    else:
        await update.message.reply_text(
            "Используй <code>/battle</code> для управления боями.",
            parse_mode=ParseMode.HTML,
        )


async def _finish_battle_creation(update, context, character=None):
    battle_type = context.user_data.get("battle_type", "friendly")
    game_id = context.user_data.get("battle_game_id")
    user = update.effective_user

    if not game_id:
        await update.message.reply_text("❌ Game ID не найден. Начни заново: <code>/battle</code>",
                                        parse_mode=ParseMode.HTML)
        return

    get_or_create_player(user.id, user.username, user.first_name)
    battle = create_battle(game_id, user.id, battle_type, character)

    for k in list(context.user_data.keys()):
        if k.startswith("battle_") or k in ("character", "owner_id"):
            del context.user_data[k]

    await update.message.reply_text(
        f"✅ <b>Бой создан!</b>\n"
        f"Game ID: <code>{h(game_id)}</code>\n"
        f"Тип: {'Дружеский' if battle_type == 'friendly' else 'Рейтинговый'}\n"
        f"{'Персонаж: ' + h(character) if character else ''}\n"
        f"ID боя: <code>{battle['id']}</code>\n\n"
        f"Поделись Game ID с соперником!\n"
        f"После боя заверши его через <code>/battle</code>.",
        parse_mode=ParseMode.HTML,
    )

    try:
        chat_id = update.effective_chat.id if update.effective_chat else None
        await notify_battle_created(context, battle, chat_id=chat_id)
    except Exception:
        pass


async def battle_type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if context.user_data.get("battle_step") != "awaiting_type":
        await query.answer("⛔ Сначала создай бой через меню.", show_alert=True)
        return
    owner = context.user_data.get("owner_id")
    if owner and owner != query.from_user.id:
        await query.answer("⛔ Это не твоя кнопка.", show_alert=True)
        return

    context.user_data["battle_type"] = query.data.replace("type_", "")
    context.user_data["battle_step"] = "awaiting_character"

    rows = []
    for i in range(0, len(POPULAR_CHARACTERS), 3):
        rows.append([
            InlineKeyboardButton(c, callback_data=f"char_{c}")
            for c in POPULAR_CHARACTERS[i:i+3]
        ])
    rows.append([InlineKeyboardButton("✏️ Свой вариант", callback_data="char_custom")])
    rows.append([InlineKeyboardButton("⏭ Пропустить", callback_data="char_skip")])

    await query.edit_message_text(
        "<b>Выбери персонажа (или пропусти):</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def battle_choose_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if context.user_data.get("battle_step") != "awaiting_character":
        await query.answer("⛔ Сначала выбери тип боя.", show_alert=True)
        return
    owner = context.user_data.get("owner_id")
    if owner and owner != query.from_user.id:
        await query.answer("⛔ Это не твоя кнопка.", show_alert=True)
        return

    data = query.data.replace("char_", "")
    user = query.from_user
    battle_type = context.user_data.get("battle_type", "friendly")
    game_id = context.user_data.get("battle_game_id")

    if data == "skip":
        get_or_create_player(user.id, user.username, user.first_name)
        battle = create_battle(game_id, user.id, battle_type, None)
        for k in list(context.user_data.keys()):
            if k.startswith("battle_") or k in ("character", "owner_id"):
                del context.user_data[k]
        await query.edit_message_text(
            f"✅ <b>Бой создан!</b>\nGame ID: <code>{h(game_id)}</code>\n"
            f"Тип: {'Дружеский' if battle_type == 'friendly' else 'Рейтинговый'}\n"
            f"ID боя: <code>{battle['id']}</code>\n\nПоделись Game ID!",
            parse_mode=ParseMode.HTML,
        )
        try:
            chat_id = query.message.chat_id if query.message else None
            await notify_battle_created(context, battle, chat_id=chat_id)
        except Exception:
            pass

    elif data == "custom":
        context.user_data["battle_step"] = "awaiting_character_name"
        await query.edit_message_text("✏️ Напиши название персонажа в ответном сообщении:")

    else:
        get_or_create_player(user.id, user.username, user.first_name)
        battle = create_battle(game_id, user.id, battle_type, data)
        for k in list(context.user_data.keys()):
            if k.startswith("battle_") or k in ("character", "owner_id"):
                del context.user_data[k]
        await query.edit_message_text(
            f"✅ <b>Бой создан!</b>\nGame ID: <code>{h(game_id)}</code>\n"
            f"Тип: {'Дружеский' if battle_type == 'friendly' else 'Рейтинговый'}\n"
            f"Персонаж: {h(data)}\nID боя: <code>{battle['id']}</code>\n\nПоделись Game ID!",
            parse_mode=ParseMode.HTML,
        )
        try:
            chat_id = query.message.chat_id if query.message else None
            await notify_battle_created(context, battle, chat_id=chat_id)
        except Exception:
            pass


async def battle_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    owner = context.user_data.get("menu_owner")
    if owner and owner != query.from_user.id:
        await query.answer("⛔ Это не твоё меню.", show_alert=True)
        return

    all_battles = battles.all()
    waiting = {
        k: v for k, v in all_battles.items()
        if v["status"] == "waiting" and v["creator_id"] != str(query.from_user.id)
    }

    if not waiting:
        await query.edit_message_text(
            "😕 Нет открытых боёв для присоединения.\nСоздай свой через меню!"
        )
        return

    keyboard = []
    for bid, b in list(waiting.items())[:10]:
        creator = get_player(b["creator_id"]) or {}
        char_info = f" [{b.get('character_creator', '?')}]" if b.get("character_creator") else ""
        label = f"{creator.get('first_name', 'Игрок')}{char_info} — {b.get('game_id', '?')}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"join_{bid}")])

    keyboard.append([InlineKeyboardButton("◀ Назад", callback_data="battle_back")])
    await query.edit_message_text(
        "<b>🔍 Доступные бои (чужие):</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def battle_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    battle_id = query.data.replace("join_", "")
    battle = join_battle(battle_id, query.from_user.id)
    if not battle:
        await query.edit_message_text("❌ Не удалось присоединиться. Бой уже занят или отменён.")
        return

    creator = get_player(battle["creator_id"]) or {}

    rows = []
    for i in range(0, len(POPULAR_CHARACTERS), 3):
        rows.append([
            InlineKeyboardButton(c, callback_data=f"oppchar_{battle_id}_{c}")
            for c in POPULAR_CHARACTERS[i:i+3]
        ])
    rows.append([InlineKeyboardButton("✏️ Свой вариант", callback_data=f"oppchar_{battle_id}_custom")])
    rows.append([InlineKeyboardButton("⏭ Пропустить", callback_data=f"oppchar_{battle_id}_skip")])

    context.user_data["join_battle_id"] = battle_id

    await query.edit_message_text(
        f"✅ <b>Ты присоединился к бою!</b>\n\n"
        f"Game ID: <code>{h(battle['game_id'])}</code>\n"
        f"Создатель: {h(creator.get('first_name', 'Игрок'))}\n"
        f"Тип: {battle['type']}\n\n"
        f"<b>Укажи своего персонажа:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(rows),
    )

    try:
        await notify_battle_joined(context, battle, query.from_user.id)
    except Exception:
        pass


async def battle_opponent_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.replace("oppchar_", "")
    parts = data.split("_", 1)
    if len(parts) < 2:
        await query.edit_message_text("❌ Ошибка данных.")
        return
    battle_id = parts[0]
    char_data = parts[1]

    if char_data == "skip":
        await query.edit_message_text("✅ Персонаж не указан. Удачного боя! ⚔️")
    elif char_data == "custom":
        context.user_data["battle_step"] = "awaiting_opponent_character"
        context.user_data["opp_char_battle_id"] = battle_id
        context.user_data["owner_id"] = query.from_user.id
        await query.edit_message_text("✏️ Напиши название персонажа в ответном сообщении:")
    else:
        set_battle_character(battle_id, query.from_user.id, char_data)
        await query.edit_message_text(
            f"✅ Персонаж: <b>{h(char_data)}</b>. Удачного боя! ⚔️",
            parse_mode=ParseMode.HTML,
        )


async def battle_screenshot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    owner = context.user_data.get("menu_owner")
    if owner and owner != query.from_user.id:
        await query.answer("⛔ Это не твоё меню.", show_alert=True)
        return

    user_id = str(query.from_user.id)
    active = {
        k: v for k, v in battles.all().items()
        if v["status"] in ("waiting", "active")
        and (v["creator_id"] == user_id or v.get("opponent_id") == user_id)
    }

    if not active:
        await query.edit_message_text("😕 У тебя нет активных боёв.")
        return

    keyboard = [
        [InlineKeyboardButton(
            f"📸 {b.get('game_id', '?')} vs {get_player(b['opponent_id'] if b['creator_id'] == user_id else b['creator_id']).get('first_name', '???')}",
            callback_data=f"ss_{bid}",
        )]
        for bid, b in active.items()
    ]
    await query.edit_message_text(
        "<b>📸 Выбери бой для скриншота:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def battle_screenshot_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    battle_id = query.data.replace("ss_", "")
    context.user_data["battle_step"] = "awaiting_screenshot_battle_id"
    context.user_data["screenshot_battle_id"] = battle_id
    context.user_data["owner_id"] = query.from_user.id
    await query.edit_message_text(
        "📸 Отправь <b>фото</b> (скриншот результата боя):",
        parse_mode=ParseMode.HTML,
    )


async def battle_screenshot_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    step = context.user_data.get("battle_step")
    if step != "awaiting_screenshot_battle_id":
        return

    owner = context.user_data.get("owner_id")
    if owner and owner != user.id:
        return

    battle_id = context.user_data.get("screenshot_battle_id")
    if not battle_id:
        return

    photo = update.message.photo[-1]
    add_screenshot(battle_id, photo.file_id)

    context.user_data.pop("battle_step", None)
    context.user_data.pop("screenshot_battle_id", None)
    context.user_data.pop("owner_id", None)
    await update.message.reply_text("✅ Скриншот загружен!")


async def battle_complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    owner = context.user_data.get("menu_owner")
    if owner and owner != query.from_user.id:
        await query.answer("⛔ Это не твоё меню.", show_alert=True)
        return

    user_id = str(query.from_user.id)
    active = {
        k: v for k, v in battles.all().items()
        if v["status"] == "active"
        and (v["creator_id"] == user_id or v.get("opponent_id") == user_id)
    }

    if not active:
        await query.edit_message_text("😕 Нет активных боёв.")
        return

    keyboard = []
    for bid, b in active.items():
        opp_id = b["opponent_id"] if b["creator_id"] == user_id else b["creator_id"]
        opp = get_player(opp_id) or {}
        label = f"⚔️ {b.get('game_id', '?')} vs {opp.get('first_name', opp_id[:6])}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"cw_{bid}")])

    await query.edit_message_text(
        "<b>✅ Выбери бой для завершения:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def battle_choose_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    battle_id = query.data.replace("cw_", "")
    context.user_data["battle_complete_id"] = battle_id
    context.user_data["owner_id"] = query.from_user.id
    battle = battles.get(battle_id)

    if not battle:
        await query.edit_message_text("❌ Бой не найден.")
        return

    creator = get_player(battle["creator_id"]) or {}
    opponent = get_player(battle.get("opponent_id")) or {}

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"🏆 {creator.get('first_name', 'Игрок 1')}",
            callback_data=f"winner_{battle['creator_id']}",
        )],
        [InlineKeyboardButton(
            f"🏆 {opponent.get('first_name', 'Игрок 2')}",
            callback_data=f"winner_{battle['opponent_id']}",
        )],
    ])
    await query.edit_message_text("Кто победил?", reply_markup=keyboard)


async def battle_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    owner = context.user_data.get("owner_id")
    if owner and owner != query.from_user.id:
        await query.answer("⛔ Это не твой выбор победителя.", show_alert=True)
        return

    winner_id = query.data.replace("winner_", "")
    battle_id = context.user_data.get("battle_complete_id")
    battle = complete_battle(battle_id, winner_id)

    context.user_data.pop("battle_complete_id", None)
    context.user_data.pop("owner_id", None)

    if not battle:
        await query.edit_message_text("❌ Ошибка при завершении боя.")
        return

    winner = get_player(winner_id) or {}

    newly_earned = check_and_award(winner_id)
    for ach in newly_earned:
        await notify_achievement(context, winner_id, ach)

    loser_id = battle["opponent_id"] if battle["creator_id"] == winner_id else battle["creator_id"]
    newly_earned_loser = check_and_award(loser_id)
    for ach in newly_earned_loser:
        await notify_achievement(context, loser_id, ach)

    text = (
        f"✅ <b>Бой завершён!</b>\n"
        f"Game ID: <code>{h(battle['game_id'])}</code>\n"
        f"Победитель: {h(winner.get('first_name', 'Игрок'))} 🏆\n\n"
        f"Рейтинг обновлён!"
    )
    if newly_earned:
        text += f"\n🎉 Новое достижение: {newly_earned[0]['icon']} {h(newly_earned[0]['name'])}!"

    await query.edit_message_text(text, parse_mode=ParseMode.HTML)


async def battle_cancel_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    owner = context.user_data.get("menu_owner")
    if owner and owner != query.from_user.id:
        await query.answer("⛔ Это не твоё меню.", show_alert=True)
        return

    user_id = str(query.from_user.id)
    own = {
        k: v for k, v in battles.all().items()
        if v["status"] in ("waiting", "active") and v["creator_id"] == user_id
    }

    if not own:
        await query.edit_message_text("😕 Нет твоих активных боёв для отмены.")
        return

    keyboard = []
    for bid, b in own.items():
        status = "ожидание" if b["status"] == "waiting" else "в бою"
        label = f"{b.get('game_id', '?')} ({status})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"cancel_{bid}")])

    await query.edit_message_text(
        "<b>❌ Выбери бой для отмены:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def battle_cancel_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    battle_id = query.data.replace("cancel_", "")
    battle = cancel_battle(battle_id)
    if not battle:
        await query.edit_message_text("❌ Бой не найден.")
        return
    await query.edit_message_text(f"❌ Бой <code>{h(battle['game_id'])}</code> отменён.", parse_mode=ParseMode.HTML)


async def battles_list_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_battles = battles.all()
    active = {k: v for k, v in all_battles.items() if v["status"] != "completed"}

    if not active:
        await update.message.reply_text("😕 Нет активных боёв.")
        return

    user_id = str(update.effective_user.id) if update.effective_user else None
    lines = ["<b>📋 Все активные бои:</b>\n"]
    for b in list(active.values())[:15]:
        creator = get_player(b["creator_id"]) or {}
        opponent = get_player(b.get("opponent_id")) if b.get("opponent_id") else None
        opp_text = h(opponent.get("first_name", "???")) if opponent else "ожидание"
        status = "🟢" if b["status"] == "waiting" else "⚔️"
        mine = " ← Ты" if user_id and (
            b["creator_id"] == user_id or b.get("opponent_id") == user_id
        ) else ""
        char_info = f" [{h(b.get('character_creator', '?'))}]" if b.get("character_creator") else ""
        lines.append(f"{status} <code>{h(b['game_id'])}</code>{char_info} | {h(creator.get('first_name', '?'))} vs {opp_text}{mine}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
