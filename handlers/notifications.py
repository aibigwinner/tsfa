import asyncio
import logging

from telegram.ext import ContextTypes

from storage import get_player

logger = logging.getLogger(__name__)


async def notify_battle_created(context: ContextTypes.DEFAULT_TYPE, battle, chat_id: int = None):
    creator = get_player(battle["creator_id"]) or {}
    text = (
        f"🎮 **Новый бой создан!**\n"
        f"Game ID: `{battle['game_id']}`\n"
        f"Создатель: {creator.get('first_name', 'Игрок')}\n"
        f"Статус: ожидание соперника\n\n"
        f"`/battles` — посмотреть активные бои"
    )
    if chat_id is None and hasattr(context, '_chat_id'):
        chat_id = getattr(context, '_chat_id', None)
    if chat_id:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"notify_battle_created: {e}")


async def notify_battle_joined(context: ContextTypes.DEFAULT_TYPE, battle, joiner_id):
    creator_id = battle["creator_id"]
    joiner = get_player(joiner_id) or {}

    try:
        await context.bot.send_message(
            chat_id=int(creator_id),
            text=(
                f"⚔️ **К твоему бою присоединились!**\n"
                f"`{battle['game_id']}`\n"
                f"Соперник: {joiner.get('first_name', 'Игрок')}\n\n"
                f"Удачного боя!"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"notify_battle_joined creator: {e}")

    try:
        await context.bot.send_message(
            chat_id=int(joiner_id),
            text=(
                f"✅ **Ты присоединился к бою!**\n"
                f"`{battle['game_id']}`\n"
                f"Создатель: {get_player(creator_id).get('first_name', 'Игрок')}\n\n"
                f"После боя заверши его через `/battle`"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"notify_battle_joined joiner: {e}")


async def notify_tournament_start(context: ContextTypes.DEFAULT_TYPE, tournament):
    for p in tournament.get("players", []):
        uid = p["id"] if isinstance(p, dict) else p
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=(
                    f"🏆 **Турнир начался!**\n"
                    f"`{tournament['name']}`\n\n"
                    f"Сетка: `/bracket {tournament['id']}`"
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"notify_tournament_start {uid}: {e}")


async def notify_achievement(context: ContextTypes.DEFAULT_TYPE, user_id, achievement):
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=(
                f"🎉 **Новое достижение!**\n"
                f"{achievement['icon']} **{achievement['name']}**\n"
                f"{achievement['desc']}\n\n"
                f"`/achievements` — все достижения"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"notify_achievement {user_id}: {e}")


async def delayed_notify(context, chat_id, text, delay_seconds=300):
    await asyncio.sleep(delay_seconds)
    try:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"delayed_notify: {e}")
