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


async def battle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Создать бой", callback_data="battle_create")],
        [InlineKeyboardButton("🔍 Найти бой", callback_data="battle_list")],
        [InlineKeyboardButton("📸 Загрузить скриншот", callback_data="battle_screenshot")],
        [InlineKeyboardButton("✅ Завершить бой", callback_data="battle_complete")],
        [InlineKeyboardButton("❌ Отменить бой", callback_data="battle_cancel")],
    ])
    text = "**🎮 Управление боями:**\nВыбери действие:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def battle_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["battle_step"] = "awaiting_game_id"
    await query.edit_message_text(
        "Введи **Game ID** из игры (который виден при создании боя):\n"
        "Отправь ID в ответном сообщении.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def battle_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("battle_step")

    if step == "awaiting_game_id":
        context.user_data["battle_game_id"] = update.message.text.strip()
        context.user_data["battle_step"] = "awaiting_type"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤝 Дружеский", callback_data="type_friendly")],
            [InlineKeyboardButton("🏆 Рейтинговый", callback_data="type_ranked")],
        ])
        await update.message.reply_text("Выбери тип боя:", reply_markup=keyboard)

    elif step == "awaiting_screenshot_battle_id":
        await _handle_screenshot_text(update, context)

    elif step == "awaiting_character_name":
        char = update.message.text.strip()
        context.user_data["character"] = char
        context.user_data.pop("battle_step", None)
        await _finish_battle_creation(update, context, char)

    else:
        await update.message.reply_text(
            "Используй `/battle` для управления боями.",
            parse_mode=ParseMode.MARKDOWN,
        )


async def _finish_battle_creation(update, context, character=None):
    battle_type = context.user_data.get("battle_type", "friendly")
    game_id = context.user_data.get("battle_game_id")
    user = update.effective_user
    get_or_create_player(user.id, user.username, user.first_name)

    battle = create_battle(game_id, user.id, battle_type, character)
    context.user_data.pop("battle_step", None)
    context.user_data.pop("battle_game_id", None)
    context.user_data.pop("battle_type", None)
    context.user_data.pop("character", None)

    await update.message.reply_text(
        f"✅ **Бой создан!**\n"
        f"Game ID: `{game_id}`\n"
        f"Тип: {'Дружеский' if battle_type == 'friendly' else 'Рейтинговый'}\n"
        f"{'Персонаж: ' + character if character else ''}\n"
        f"ID боя: `{battle['id']}`\n\n"
        f"Поделись Game ID с соперником!\n"
        f"После боя заверши его через `/battle`.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def battle_type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    battle_type = query.data.replace("type_", "")
    context.user_data["battle_type"] = battle_type

    rows = []
    for i in range(0, len(POPULAR_CHARACTERS), 3):
        chunk = POPULAR_CHARACTERS[i:i + 3]
        rows.append([
            InlineKeyboardButton(c, callback_data=f"char_{c}")
            for c in chunk
        ])
    rows.append([InlineKeyboardButton("✏️ Свой вариант", callback_data="char_custom")])
    rows.append([InlineKeyboardButton("⏭ Пропустить", callback_data="char_skip")])

    await query.edit_message_text(
        "**Выбери персонажа (или пропусти):**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def battle_choose_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.replace("char_", "")

    if data == "skip":
        context.user_data["character"] = None
        user = query.from_user
        char = None
        battle_type = context.user_data.get("battle_type", "friendly")
        game_id = context.user_data.get("battle_game_id")
        get_or_create_player(user.id, user.username, user.first_name)
        battle = create_battle(game_id, user.id, battle_type, None)
        context.user_data.pop("battle_step", None)
        context.user_data.pop("battle_game_id", None)
        context.user_data.pop("battle_type", None)
        await query.edit_message_text(
            f"✅ **Бой создан!**\n"
            f"Game ID: `{game_id}`\n"
            f"Тип: {'Дружеский' if battle_type == 'friendly' else 'Рейтинговый'}\n"
            f"ID боя: `{battle['id']}`\n\n"
            f"Поделись Game ID с соперником!",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "custom":
        context.user_data["battle_step"] = "awaiting_character_name"
        await query.edit_message_text("✏️ Напиши название персонажа в ответном сообщении:")

    else:
        context.user_data["character"] = data
        user = query.from_user
        battle_type = context.user_data.get("battle_type", "friendly")
        game_id = context.user_data.get("battle_game_id")
        get_or_create_player(user.id, user.username, user.first_name)
        battle = create_battle(game_id, user.id, battle_type, data)
        context.user_data.pop("battle_step", None)
        context.user_data.pop("battle_game_id", None)
        context.user_data.pop("battle_type", None)
        context.user_data.pop("character", None)
        await query.edit_message_text(
            f"✅ **Бой создан!**\n"
            f"Game ID: `{game_id}`\n"
            f"Тип: {'Дружеский' if battle_type == 'friendly' else 'Рейтинговый'}\n"
            f"Персонаж: {data}\n"
            f"ID боя: `{battle['id']}`\n\n"
            f"Поделись Game ID с соперником!",
            parse_mode=ParseMode.MARKDOWN,
        )


async def battle_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
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
        "**🔍 Доступные бои:**",
        parse_mode=ParseMode.MARKDOWN,
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
        chunk = POPULAR_CHARACTERS[i:i + 3]
        rows.append([
            InlineKeyboardButton(c, callback_data=f"oppchar_{battle_id}_{c}")
            for c in chunk
        ])
    rows.append([InlineKeyboardButton("✏️ Свой вариант", callback_data=f"oppchar_{battle_id}_custom")])
    rows.append([InlineKeyboardButton("⏭ Пропустить", callback_data=f"oppchar_{battle_id}_skip")])

    context.user_data["join_battle_id"] = battle_id

    await query.edit_message_text(
        f"✅ **Ты присоединился к бою!**\n\n"
        f"Game ID: `{battle['game_id']}`\n"
        f"Создатель: {creator.get('first_name', 'Игрок')}\n"
        f"Тип: {battle['type']}\n\n"
        f"**Укажи своего персонажа:**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def battle_opponent_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.replace("oppchar_", "")
    parts = data.split("_", 1)
    battle_id = parts[0]
    char_data = parts[1] if len(parts) > 1 else "skip"

    if char_data == "skip":
        await query.edit_message_text("✅ Персонаж не указан. Удачного боя! ⚔️")
    elif char_data == "custom":
        context.user_data["battle_step"] = "awaiting_opponent_character"
        context.user_data["opp_char_battle_id"] = battle_id
        await query.edit_message_text("✏️ Напиши название персонажа в ответном сообщении:")
    else:
        set_battle_character(battle_id, query.from_user.id, char_data)
        await query.edit_message_text(f"✅ Персонаж: **{char_data}**. Удачного боя! ⚔️", parse_mode=ParseMode.MARKDOWN)


async def battle_screenshot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    active = {
        k: v for k, v in battles.all().items()
        if v["status"] in ("waiting", "active")
        and (v["creator_id"] == user_id or v.get("opponent_id") == user_id)
    }

    if not active:
        await query.edit_message_text("😕 У тебя нет активных боёв.")
        return

    keyboard = []
    for bid, b in active.items():
        opp_id = b["opponent_id"] if b["creator_id"] == user_id else b["creator_id"]
        opp = get_player(opp_id) or {}
        label = f"📸 {b.get('game_id', '?')} vs {opp.get('first_name', '???')}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"ss_{bid}")])

    await query.edit_message_text(
        "**📸 Выбери бой для загрузки скриншота:**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def battle_screenshot_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    battle_id = query.data.replace("ss_", "")
    context.user_data["battle_step"] = "awaiting_screenshot_battle_id"
    context.user_data["screenshot_battle_id"] = battle_id
    await query.edit_message_text(
        "📸 Отправь **фото** (скриншот результата боя):",
        parse_mode=ParseMode.MARKDOWN,
    )


async def _handle_screenshot_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    battle_id = context.user_data.get("screenshot_battle_id")
    if not battle_id:
        await update.message.reply_text("❌ Ошибка. Начни заново через `/battle`.", parse_mode=ParseMode.MARKDOWN)
        context.user_data.pop("battle_step", None)
        return
    await update.message.reply_text("❌ Это не фото. Отправь **изображение** (скриншот).", parse_mode=ParseMode.MARKDOWN)


async def battle_screenshot_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("battle_step")
    if step != "awaiting_screenshot_battle_id":
        return

    battle_id = context.user_data.get("screenshot_battle_id")
    if not battle_id:
        return

    photo = update.message.photo[-1]
    file_id = photo.file_id
    add_screenshot(battle_id, file_id)

    context.user_data.pop("battle_step", None)
    context.user_data.pop("screenshot_battle_id", None)
    await update.message.reply_text("✅ Скриншот загружен!")


async def battle_complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
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
        char_info = f" [{b.get('character_creator', '?')}]" if b.get("character_creator") else ""
        label = f"⚔️ {b.get('game_id', '?')}{char_info} vs {opp.get('first_name', opp_id[:6])}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"cw_{bid}")])

    await query.edit_message_text(
        "**✅ Выбери бой для завершения:**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def battle_choose_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    battle_id = query.data.replace("cw_", "")
    context.user_data["battle_complete_id"] = battle_id
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
    winner_id = query.data.replace("winner_", "")
    battle_id = context.user_data.get("battle_complete_id")
    battle = complete_battle(battle_id, winner_id)
    context.user_data.pop("battle_complete_id", None)

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
        f"✅ **Бой завершён!**\n"
        f"Game ID: `{battle['game_id']}`\n"
        f"Победитель: {winner.get('first_name', 'Игрок')} 🏆\n\n"
        f"Рейтинг обновлён!"
    )
    if newly_earned:
        text += f"\n🎉 Новое достижение: {newly_earned[0]['icon']} {newly_earned[0]['name']}!"

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)


async def battle_cancel_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    own = {
        k: v for k, v in battles.all().items()
        if v["status"] in ("waiting", "active") and v["creator_id"] == user_id
    }

    if not own:
        await query.edit_message_text("😕 Нет созданных тобой активных боёв.")
        return

    keyboard = []
    for bid, b in own.items():
        label = f"{b.get('game_id', '?')} ({'ожидание' if b['status'] == 'waiting' else 'в бою'})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"cancel_{bid}")])

    await query.edit_message_text(
        "**❌ Выбери бой для отмены:**",
        parse_mode=ParseMode.MARKDOWN,
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
    await query.edit_message_text(f"❌ Бой `{battle['game_id']}` отменён.", parse_mode=ParseMode.MARKDOWN)


async def battles_list_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_battles = battles.all()
    active = {k: v for k, v in all_battles.items() if v["status"] != "completed"}

    if not active:
        await update.message.reply_text("😕 Нет активных боёв.")
        return

    lines = ["**📋 Активные бои:**\n"]
    for b in list(active.values())[:10]:
        creator = get_player(b["creator_id"]) or {}
        opponent = get_player(b.get("opponent_id")) if b.get("opponent_id") else None
        opp_text = opponent.get("first_name", "???") if opponent else "ожидание"
        status = "🟢" if b["status"] == "waiting" else "⚔️"
        char_info = f" [{b.get('character_creator', '?')}]" if b.get("character_creator") else ""
        lines.append(f"{status} `{b['game_id']}`{char_info} | {creator.get('first_name', '?')} vs {opp_text}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
