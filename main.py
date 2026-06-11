import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters,
)
from telegram.constants import ParseMode
import traceback

from config import BOT_TOKEN
from storage import players
from handlers.start import start, help_command
from handlers.profile import profile, leaderboard, leaderboard_callback, profile_achievements_callback
from handlers.battle import (
    battle_menu, battle_create, battle_handle_text, battle_type_chosen,
    battle_choose_character, battle_list, battle_join, battle_opponent_character,
    battle_screenshot_start, battle_screenshot_choose, battle_screenshot_photo,
    battle_complete, battle_choose_winner, battle_finish,
    battle_cancel_list, battle_cancel_confirm, battles_list_all,
)
from handlers.tournament import (
    tournament_menu, tournament_register, tournament_start,
    tournament_advance, tournament_view_bracket, tournament_bracket_cmd,
)
from handlers.admin import (
    announce, challenge_create, tournament_new, ban_player, unban_player,
)
from handlers.voting import poll_create, poll_vote, poll_close
from handlers.achievements import achievements_list

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def build_application(post_init=None):
    builder = ApplicationBuilder().token(BOT_TOKEN)
    if post_init:
        builder.post_init(post_init)
    app = builder.build()

    # Basic commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("battles", battles_list_all))
    app.add_handler(CommandHandler("battle", battle_menu))
    app.add_handler(CommandHandler("achievements", achievements_list))

    # Tournament commands
    app.add_handler(CommandHandler("tournament", tournament_menu))
    app.add_handler(CommandHandler("bracket", tournament_bracket_cmd))
    app.add_handler(CommandHandler("tournament_start", tournament_start))
    app.add_handler(CommandHandler("tadvance", tournament_advance))

    # Admin commands
    app.add_handler(CommandHandler("announce", announce))
    app.add_handler(CommandHandler("challenge", challenge_create))
    app.add_handler(CommandHandler("tournament_new", tournament_new))
    app.add_handler(CommandHandler("ban", ban_player))
    app.add_handler(CommandHandler("unban", unban_player))
    app.add_handler(CommandHandler("poll", poll_create))

    # Battle callbacks
    app.add_handler(CallbackQueryHandler(battle_create, pattern="^battle_create$"))
    app.add_handler(CallbackQueryHandler(battle_type_chosen, pattern="^type_"))
    app.add_handler(CallbackQueryHandler(battle_choose_character, pattern="^char_"))
    app.add_handler(CallbackQueryHandler(battle_list, pattern="^battle_list$"))
    app.add_handler(CallbackQueryHandler(battle_join, pattern="^join_"))
    app.add_handler(CallbackQueryHandler(battle_opponent_character, pattern="^oppchar_"))
    app.add_handler(CallbackQueryHandler(battle_screenshot_start, pattern="^battle_screenshot$"))
    app.add_handler(CallbackQueryHandler(battle_screenshot_choose, pattern="^ss_"))
    app.add_handler(CallbackQueryHandler(battle_complete, pattern="^battle_complete$"))
    app.add_handler(CallbackQueryHandler(battle_choose_winner, pattern="^cw_"))
    app.add_handler(CallbackQueryHandler(battle_finish, pattern="^winner_"))
    app.add_handler(CallbackQueryHandler(battle_cancel_list, pattern="^battle_cancel$"))
    app.add_handler(CallbackQueryHandler(battle_cancel_confirm, pattern="^cancel_"))
    app.add_handler(CallbackQueryHandler(battle_menu, pattern="^battle_back$"))

    # Tournament callbacks
    app.add_handler(CallbackQueryHandler(tournament_register, pattern="^treg_"))
    app.add_handler(CallbackQueryHandler(tournament_view_bracket, pattern="^tbracket_"))

    # Voting callbacks
    app.add_handler(CallbackQueryHandler(poll_vote, pattern="^vote_"))
    app.add_handler(CallbackQueryHandler(poll_close, pattern="^poll_close_"))

    # Profile callbacks
    app.add_handler(CallbackQueryHandler(leaderboard_callback, pattern="^leaderboard$"))
    app.add_handler(CallbackQueryHandler(profile_achievements_callback, pattern="^achievements$"))

    # Photos (screenshots)
    app.add_handler(MessageHandler(filters.PHOTO, battle_screenshot_photo))

    # Text handler (game ID, custom character name, etc.)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, battle_handle_text))

    app.add_error_handler(error_handler)

    return app


async def error_handler(update: Update, context):
    logging.error(f"Exception: {context.error}")
    traceback.print_exception(type(context.error), context.error, context.error.__traceback__)
    try:
        user = update.effective_user
        if user:
            player = players.get(str(user.id))
            if player and player.get("is_admin"):
                tb = "".join(traceback.format_exception(type(context.error), context.error, context.error.__traceback__))
                await context.bot.send_message(
                    user.id,
                    f"❌ **Ошибка:**\n`{str(context.error)[:200]}`",
                    parse_mode=ParseMode.MARKDOWN,
                )
    except Exception:
        pass


def main():
    app = build_application()
    logging.info("Shadow Fight Arena Bot запущен (polling)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
