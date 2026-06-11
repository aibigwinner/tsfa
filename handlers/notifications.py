import asyncio
import html
import logging

from telegram.ext import ContextTypes

from storage import get_player

h = html.escape
logger = logging.getLogger(__name__)


async def notify_battle_created(context: ContextTypes.DEFAULT_TYPE, battle, chat_id: int = None):
    creator = get_player(battle["creator_id"]) or {}
    text = (
        f"🎮 <b>Новый бой создан!</b>\n"
        f"Game ID: <code>{h(battle['game_id'])}</code>\n"
        f"Создатель: {h(creator.get('first_name', 'Игрок'))}\n"
        f"Статус: ожидание соперника\n\n"
        f"<code>/battles</code> — посмотреть активные бои"
    )
    if chat_id is None and hasattr(context, '_chat_id'):
        chat_id = getattr(context, '_chat_id', None)
    if chat_id:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"notify_battle_created: {e}")


async def notify_battle_joined(context: ContextTypes.DEFAULT_TYPE, battle, joiner_id):
    creator_id = battle["creator_id"]
    joiner = get_player(joiner_id) or {}

    try:
        await context.bot.send_message(
            chat_id=int(creator_id),
            text=(
                f"⚔️ <b>К твоему бою присоединились!</b>\n"
                f"<code>{h(battle['game_id'])}</code>\n"
                f"Соперник: {h(joiner.get('first_name', 'Игрок'))}\n\n"
                f"Удачного боя!"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"notify_battle_joined creator: {e}")

    try:
        await context.bot.send_message(
            chat_id=int(joiner_id),
            text=(
                f"✅ <b>Ты присоединился к бою!</b>\n"
                f"<code>{h(battle['game_id'])}</code>\n"
                f"Создатель: {h(get_player(creator_id).get('first_name', 'Игрок'))}\n\n"
                f"После боя заверши его через <code>/battle</code>"
            ),
            parse_mode="HTML",
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
                    f"🏆 <b>Турнир начался!</b>\n"
                    f"<code>{h(tournament['name'])}</code>\n\n"
                    f"Сетка: <code>/bracket {tournament['id']}</code>"
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"notify_tournament_start {uid}: {e}")


async def notify_achievement(context: ContextTypes.DEFAULT_TYPE, user_id, achievement):
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=(
                f"🎉 <b>Новое достижение!</b>\n"
                f"{achievement['icon']} <b>{h(achievement['name'])}</b>\n"
                f"{h(achievement['desc'])}\n\n"
                f"<code>/achievements</code> — все достижения"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"notify_achievement {user_id}: {e}")


async def delayed_notify(context, chat_id, text, delay_seconds=300):
    await asyncio.sleep(delay_seconds)
    try:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"delayed_notify: {e}")
