import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from config import BOT_TOKEN
import database as db
import handlers
import admin

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states (must match handlers.py)
CHOOSE_CANDIDATE, ENTER_BET_AMOUNT = range(2)
CHOOSE_PAYMENT, ENTER_TX_HASH, ENTER_AMOUNT = range(3)
SET_WALLET_ADDRESS = 0


def main():
    db.init_db()

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in environment variables!")

    app = Application.builder().token(BOT_TOKEN).build()

    # ── Deposit conversation ──────────────────────────────────────────────────
    deposit_conv = ConversationHandler(
        entry_points=[
            CommandHandler("confirm_deposit", handlers.confirm_deposit_start),
            CallbackQueryHandler(handlers.confirm_deposit_start, pattern="^deposit_submit$"),
        ],
        states={
            CHOOSE_PAYMENT: [
                CallbackQueryHandler(handlers.deposit_choose_payment, pattern="^pay_"),
                CallbackQueryHandler(handlers.cancel, pattern="^cancel$"),
            ],
            ENTER_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.deposit_enter_amount)
            ],
            ENTER_TX_HASH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.deposit_enter_tx)
            ],
        },
        fallbacks=[CommandHandler("cancel", handlers.cancel)],
    )

    # ── Bet conversation ──────────────────────────────────────────────────────
    bet_conv = ConversationHandler(
        entry_points=[CommandHandler("bet", handlers.bet_start)],
        states={
            CHOOSE_CANDIDATE: [
                CallbackQueryHandler(handlers.bet_choose_candidate, pattern="^bet_"),
                CallbackQueryHandler(handlers.bet_cancel, pattern="^cancel$"),
            ],
            ENTER_BET_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.bet_enter_amount),
                CallbackQueryHandler(handlers.bet_confirm, pattern="^confirm_bet$"),
                CallbackQueryHandler(handlers.bet_cancel, pattern="^cancel_bet$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", handlers.cancel)],
    )

    # ── Wallet set conversation (admin) ───────────────────────────────────────
    wallet_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin.admin_callback, pattern="^setwallet_"),
        ],
        states={
            SET_WALLET_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin.receive_wallet_address)
            ],
        },
        fallbacks=[CommandHandler("cancel", handlers.cancel)],
    )

    # ── Register handlers ─────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(CommandHandler("balance", handlers.balance))
    app.add_handler(CommandHandler("deposit", handlers.deposit))
    app.add_handler(CommandHandler("mybets", handlers.mybets))
    app.add_handler(CommandHandler("referral", handlers.referral))

    # Admin commands
    app.add_handler(CommandHandler("admin", admin.admin_panel))
    app.add_handler(CommandHandler("setwallet", admin.setwallet_command))
    app.add_handler(CommandHandler("broadcast", admin.broadcast))
    app.add_handler(CommandHandler("stats", admin.stats_command))

    # Conversations
    app.add_handler(deposit_conv)
    app.add_handler(bet_conv)
    app.add_handler(wallet_conv)

    # Generic admin callback (for non-conversation callbacks)
    app.add_handler(CallbackQueryHandler(admin.admin_callback, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(admin.admin_callback, pattern="^(confirm_dep_|reject_dep_)"))

    # General menu callbacks
    app.add_handler(CallbackQueryHandler(handlers.button_router, pattern="^menu_"))
    app.add_handler(CallbackQueryHandler(handlers.button_router, pattern="^cancel$"))

    logger.info("🤖 naija2027election_bot is starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    from keep_alive import keep_alive
    keep_alive()
    main()
