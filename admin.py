from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from config import ADMIN_IDS, CANDIDATES

# Conversation states
SET_WALLET_METHOD, SET_WALLET_ADDRESS = range(2)
BROADCAST_MESSAGE = range(1)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_only(func):
    """Decorator to restrict handler to admins."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.message.reply_text("⛔ Unauthorized. Admin only.")
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper


def admin_callback_only(func):
    """Decorator to restrict callback handler to admins."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.callback_query.answer("⛔ Unauthorized.", show_alert=True)
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper


# ─── /admin ──────────────────────────────────────────────────────────────────

@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = db.get_platform_stats()
    bet_stats = db.get_bet_stats()

    bet_lines = ""
    for b in bet_stats:
        candidate = CANDIDATES.get(b["candidate"], {}).get("name", b["candidate"])
        bet_lines += f"  • {candidate}: {b['total_bets']} bets (${b['total_staked']:.2f})\n"
    if not bet_lines:
        bet_lines = "  No bets yet.\n"

    msg = (
        f"🛠️ *Admin Panel*\n\n"
        f"📊 *Platform Stats:*\n"
        f"• Users: {stats['total_users']}\n"
        f"• Confirmed Deposits: {stats['total_deposits']} (${stats['total_deposited']:.2f})\n"
        f"• Active Bets: {stats['total_bets']} (${stats['total_staked']:.2f} staked)\n\n"
        f"🗳️ *Bets by Candidate:*\n{bet_lines}"
    )

    keyboard = [
        [InlineKeyboardButton("📥 Pending Deposits", callback_data="admin_pending"),
         InlineKeyboardButton("📋 All Deposits", callback_data="admin_all_deposits")],
        [InlineKeyboardButton("💸 Pending Withdrawals", callback_data="admin_withdrawals"),
         InlineKeyboardButton("📜 All Withdrawals", callback_data="admin_all_withdrawals")],
        [InlineKeyboardButton("💳 Set Wallets", callback_data="admin_wallets"),
         InlineKeyboardButton("👥 All Users", callback_data="admin_users")],
        [InlineKeyboardButton("🗳️ All Bets", callback_data="admin_bets"),
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")]
    ]
    await update.message.reply_text(
        msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── Admin callbacks ──────────────────────────────────────────────────────────

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("⛔ Unauthorized.", show_alert=True)
        return

    await query.answer()
    data = query.data

    if data == "admin_refresh":
        stats = db.get_platform_stats()
        bet_stats = db.get_bet_stats()
        bet_lines = ""
        for b in bet_stats:
            candidate = CANDIDATES.get(b["candidate"], {}).get("name", b["candidate"])
            bet_lines += f"  • {candidate}: {b['total_bets']} bets (${b['total_staked']:.2f})\n"
        if not bet_lines:
            bet_lines = "  No bets yet.\n"

        msg = (
            f"🛠️ *Admin Panel* (refreshed)\n\n"
            f"📊 *Platform Stats:*\n"
            f"• Users: {stats['total_users']}\n"
            f"• Confirmed Deposits: {stats['total_deposits']} (${stats['total_deposited']:.2f})\n"
            f"• Active Bets: {stats['total_bets']} (${stats['total_staked']:.2f} staked)\n\n"
            f"🗳️ *Bets by Candidate:*\n{bet_lines}"
        )
        keyboard = [
            [InlineKeyboardButton("📥 Pending Deposits", callback_data="admin_pending"),
             InlineKeyboardButton("📋 All Deposits", callback_data="admin_all_deposits")],
            [InlineKeyboardButton("💸 Pending Withdrawals", callback_data="admin_withdrawals"),
             InlineKeyboardButton("📜 All Withdrawals", callback_data="admin_all_withdrawals")],
            [InlineKeyboardButton("💳 Set Wallets", callback_data="admin_wallets"),
             InlineKeyboardButton("👥 All Users", callback_data="admin_users")],
            [InlineKeyboardButton("🗳️ All Bets", callback_data="admin_bets"),
             InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")]
        ]
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_pending":
        await show_pending_deposits(query, context)

    elif data == "admin_all_deposits":
        await show_all_deposits(query)

    elif data == "admin_withdrawals":
        await show_pending_withdrawals(query, context)

    elif data == "admin_all_withdrawals":
        await show_all_withdrawals(query)

    elif data == "admin_wallets":
        await show_wallet_menu(query)

    elif data == "admin_users":
        await show_all_users(query)

    elif data == "admin_bets":
        await show_all_bets(query)

    elif data == "admin_broadcast":
        await query.edit_message_text(
            "📢 *Broadcast Message*\n\nUse the command:\n`/broadcast Your message here`",
            parse_mode="Markdown"
        )

    elif data.startswith("confirm_dep_"):
        deposit_id = data.replace("confirm_dep_", "")
        await handle_confirm_deposit(query, context, deposit_id)

    elif data.startswith("reject_dep_"):
        deposit_id = data.replace("reject_dep_", "")
        await handle_reject_deposit(query, context, deposit_id)

    elif data.startswith("approve_wd_"):
        wd_id = data.replace("approve_wd_", "")
        await handle_approve_withdrawal(query, context, wd_id)

    elif data.startswith("reject_wd_"):
        wd_id = data.replace("reject_wd_", "")
        await handle_reject_withdrawal(query, context, wd_id)

    elif data.startswith("setwallet_"):
        method = data.replace("setwallet_", "")
        context.user_data["wallet_method"] = method
        await query.edit_message_text(
            f"✏️ *Set {method} Wallet Address*\n\nSend the new wallet address:",
            parse_mode="Markdown"
        )
        return SET_WALLET_ADDRESS


async def show_wallet_menu(query):
    wallets = db.get_wallets()
    usdt = wallets.get("USDT_TRC20", "Not set")
    sol = wallets.get("SOLANA", "Not set")
    msg = (
        f"💳 *Wallet Addresses*\n\n"
        f"USDT TRC20:\n`{usdt}`\n\n"
        f"Solana:\n`{sol}`"
    )
    keyboard = [
        [InlineKeyboardButton("✏️ Set USDT TRC20", callback_data="setwallet_USDT_TRC20")],
        [InlineKeyboardButton("✏️ Set Solana", callback_data="setwallet_SOLANA")],
    ]
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def receive_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    method = context.user_data.get("wallet_method")
    address = update.message.text.strip()

    if not method:
        await update.message.reply_text("❌ Session expired. Use /admin again.")
        return ConversationHandler.END

    db.set_wallet(method, address)
    context.user_data.clear()
    await update.message.reply_text(
        f"✅ *{method}* wallet address updated:\n`{address}`",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# ─── Show pending deposits ──────────────────────────────────────────────────

async def show_pending_deposits(query, context):
    deposits = db.get_pending_deposits()
    if not deposits:
        await query.edit_message_text("✅ No pending deposits.")
        return

    for dep in deposits[:10]:
        msg = (
            f"📥 *Pending Deposit*\n\n"
            f"🆔 ID: `{dep['id']}`\n"
            f"👤 User: {dep['full_name']} (@{dep['username']})\n"
            f"💵 Amount: ${dep['amount_usd']:.2f} USD\n"
            f"💳 Method: {dep['method']}\n"
            f"🔗 TX: `{dep['tx_hash']}`\n"
            f"📅 Date: {dep['created_at'][:19]}"
        )
        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_dep_{dep['id']}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_dep_{dep['id']}")]
        ]
        await context.bot.send_message(
            query.from_user.id,
            msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    await query.edit_message_text(f"📥 Showing {len(deposits[:10])} pending deposit(s).")


async def show_all_deposits(query):
    deposits = db.get_all_deposits()
    if not deposits:
        await query.edit_message_text("📭 No deposits found.")
        return

    lines = ["📋 *Recent Deposits (last 20):*\n"]
    for dep in deposits[:20]:
        status_emoji = {"confirmed": "✅", "pending": "⏳", "rejected": "❌"}.get(dep["status"], "⚪")
        lines.append(
            f"{status_emoji} `{dep['id']}` — ${dep['amount_usd']:.2f} — "
            f"{dep['method']} — {dep.get('username','N/A')} — {dep['created_at'][:10]}"
        )
    await query.edit_message_text("\n".join(lines), parse_mode="Markdown")


async def handle_confirm_deposit(query, context, deposit_id: str):
    success, result = db.confirm_deposit(deposit_id)
    if not success:
        await query.edit_message_text(f"❌ {result}")
        return

    dep = result["deposit"]
    referrer_id = result["referrer_id"]
    bonus_paid = result["bonus_paid"]

    await query.edit_message_text(
        f"✅ *Deposit Confirmed!*\n\n"
        f"📋 ID: `{deposit_id}`\n"
        f"💵 Amount: ${dep['amount_usd']:.2f} credited to user.",
        parse_mode="Markdown"
    )

    # Notify user
    try:
        await context.bot.send_message(
            dep["user_id"],
            f"✅ *Your deposit has been confirmed!*\n\n"
            f"💵 ${dep['amount_usd']:.2f} USD added to your balance.\n"
            f"Use /bet to place your bet now! 🇳🇬",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    # Notify referrer
    if referrer_id and bonus_paid > 0:
        try:
            await context.bot.send_message(
                referrer_id,
                f"🎉 *Referral Bonus!*\n\n"
                f"You earned *${bonus_paid:.2f} USD* referral bonus!\n"
                f"A user you referred just made their first deposit.",
                parse_mode="Markdown"
            )
        except Exception:
            pass


async def handle_reject_deposit(query, context, deposit_id: str):
    success = db.reject_deposit(deposit_id)
    if not success:
        await query.edit_message_text("❌ Could not reject deposit (already processed?).")
        return

    await query.edit_message_text(f"❌ Deposit `{deposit_id}` rejected.", parse_mode="Markdown")


# ─── /setwallet ───────────────────────────────────────────────────────────────

@admin_only
async def setwallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: `/setwallet <USDT_TRC20|SOLANA> <address>`",
            parse_mode="Markdown"
        )
        return

    method = args[0].upper()
    address = args[1]

    if method not in ("USDT_TRC20", "SOLANA"):
        await update.message.reply_text("❌ Method must be USDT_TRC20 or SOLANA.")
        return

    db.set_wallet(method, address)
    await update.message.reply_text(
        f"✅ *{method}* wallet updated:\n`{address}`",
        parse_mode="Markdown"
    )


# ─── Withdrawal management ────────────────────────────────────────────────────

async def show_pending_withdrawals(query, context):
    withdrawals = db.get_pending_withdrawals()
    if not withdrawals:
        await query.edit_message_text("✅ No pending withdrawals.")
        return

    await query.edit_message_text(f"💸 Sending {len(withdrawals[:10])} pending withdrawal(s)...")

    for wd in withdrawals[:10]:
        msg = (
            f"💸 *Pending Withdrawal*\n\n"
            f"📋 ID: `{wd['id']}`\n"
            f"👤 User: {wd['full_name']} (@{wd.get('username', 'N/A')})\n"
            f"🆔 User ID: `{wd['user_id']}`\n"
            f"💵 Amount: *${wd['amount_usd']:.2f} USD*\n"
            f"💳 Method: {wd['method']}\n"
            f"📬 Address: `{wd['address']}`\n"
            f"📅 Requested: {wd['created_at'][:19]}"
        )
        keyboard = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_wd_{wd['id']}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_wd_{wd['id']}")]
        ]
        await context.bot.send_message(
            query.from_user.id, msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def show_all_withdrawals(query):
    withdrawals = db.get_all_withdrawals()
    if not withdrawals:
        await query.edit_message_text("📭 No withdrawals found.")
        return

    lines = [f"📜 *All Withdrawals ({len(withdrawals)}):*\n"]
    for wd in withdrawals[:20]:
        emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(wd["status"], "⚪")
        lines.append(
            f"{emoji} `{wd['id']}` — ${wd['amount_usd']:.2f} — "
            f"{wd['method']} — @{wd.get('username', 'N/A')} — {wd['created_at'][:10]}"
        )
    await query.edit_message_text("\n".join(lines), parse_mode="Markdown")


async def handle_approve_withdrawal(query, context, wd_id: str):
    success, result = db.approve_withdrawal(wd_id)
    if not success:
        await query.edit_message_text(f"❌ {result}")
        return

    wd = result
    await query.edit_message_text(
        f"✅ *Withdrawal Approved!*\n\n"
        f"📋 ID: `{wd_id}`\n"
        f"💵 ${wd['amount_usd']:.2f} — {wd['method']}\n"
        f"📬 `{wd['address']}`",
        parse_mode="Markdown"
    )
    try:
        await context.bot.send_message(
            wd["user_id"],
            f"✅ *Withdrawal Approved!*\n\n"
            f"📋 ID: `{wd_id}`\n"
            f"💵 *${wd['amount_usd']:.2f} USD* is being sent to:\n`{wd['address']}`\n\n"
            f"Please allow time for the network to confirm the transaction. 🇳🇬",
            parse_mode="Markdown"
        )
    except Exception:
        pass


async def handle_reject_withdrawal(query, context, wd_id: str):
    success, result = db.reject_withdrawal(wd_id)
    if not success:
        await query.edit_message_text(f"❌ {result}")
        return

    wd = result
    await query.edit_message_text(
        f"❌ *Withdrawal Rejected*\n\n"
        f"📋 ID: `{wd_id}`\n"
        f"💵 ${wd['amount_usd']:.2f} refunded to user's balance.",
        parse_mode="Markdown"
    )
    try:
        await context.bot.send_message(
            wd["user_id"],
            f"❌ *Withdrawal Rejected*\n\n"
            f"📋 ID: `{wd_id}`\n"
            f"💵 *${wd['amount_usd']:.2f} USD* has been refunded to your balance.\n\n"
            f"Contact support if you believe this is an error.",
            parse_mode="Markdown"
        )
    except Exception:
        pass


# ─── /approve & /reject ────────────────────────────────────────────────────────

@admin_only
async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: `/approve <withdrawal_id>`", parse_mode="Markdown"
        )
        return

    wd_id = context.args[0].strip().upper()
    success, result = db.approve_withdrawal(wd_id)
    if not success:
        await update.message.reply_text(f"❌ {result}")
        return

    wd = result
    await update.message.reply_text(
        f"✅ *Withdrawal `{wd_id}` approved!*\n"
        f"💵 ${wd['amount_usd']:.2f} — {wd['method']}\n"
        f"📬 `{wd['address']}`",
        parse_mode="Markdown"
    )
    try:
        await context.bot.send_message(
            wd["user_id"],
            f"✅ *Withdrawal Approved!*\n\n"
            f"📋 ID: `{wd_id}`\n"
            f"💵 *${wd['amount_usd']:.2f} USD* is being sent to:\n`{wd['address']}`\n\n"
            f"Please allow time for the network to confirm the transaction. 🇳🇬",
            parse_mode="Markdown"
        )
    except Exception:
        pass


@admin_only
async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: `/reject <withdrawal_id>`", parse_mode="Markdown"
        )
        return

    wd_id = context.args[0].strip().upper()
    success, result = db.reject_withdrawal(wd_id)
    if not success:
        await update.message.reply_text(f"❌ {result}")
        return

    wd = result
    await update.message.reply_text(
        f"❌ *Withdrawal `{wd_id}` rejected.*\n"
        f"💵 ${wd['amount_usd']:.2f} refunded to user's balance.",
        parse_mode="Markdown"
    )
    try:
        await context.bot.send_message(
            wd["user_id"],
            f"❌ *Withdrawal Rejected*\n\n"
            f"📋 ID: `{wd_id}`\n"
            f"💵 *${wd['amount_usd']:.2f} USD* has been refunded to your balance.\n\n"
            f"Contact support if you believe this is an error.",
            parse_mode="Markdown"
        )
    except Exception:
        pass


# ─── /broadcast ───────────────────────────────────────────────────────────────

@admin_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/broadcast Your message here`", parse_mode="Markdown")
        return

    message = " ".join(context.args)
    users = db.get_all_users()
    sent = 0
    failed = 0

    for user in users:
        try:
            await context.bot.send_message(
                user["user_id"],
                f"📢 *Announcement:*\n\n{message}",
                parse_mode="Markdown"
            )
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"📢 Broadcast complete.\n✅ Sent: {sent}\n❌ Failed: {failed}"
    )


# ─── /stats ───────────────────────────────────────────────────────────────────

@admin_only
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = db.get_platform_stats()
    bet_stats = db.get_bet_stats()

    bet_lines = ""
    for b in bet_stats:
        candidate = CANDIDATES.get(b["candidate"], {}).get("name", b["candidate"])
        bet_lines += f"  • {candidate}: {b['total_bets']} bets (${b['total_staked']:.2f} staked)\n"
    if not bet_lines:
        bet_lines = "  No bets yet.\n"

    msg = (
        f"📊 *Full Platform Statistics*\n\n"
        f"👥 Total Users: {stats['total_users']}\n"
        f"💰 Confirmed Deposits: {stats['total_deposits']}\n"
        f"💵 Total Deposited: ${stats['total_deposited']:.2f} USD\n"
        f"🎯 Active Bets: {stats['total_bets']}\n"
        f"📈 Total Staked: ${stats['total_staked']:.2f} USD\n\n"
        f"🗳️ *Bets by Candidate:*\n{bet_lines}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def show_all_users(query):
    users = db.get_all_users()
    if not users:
        await query.edit_message_text("📭 No users found.")
        return

    lines = [f"👥 *All Users ({len(users)}):*\n"]
    for u in users[:20]:
        lines.append(
            f"• {u['full_name']} (@{u.get('username','N/A')}) — "
            f"${u['balance_usd']:.2f} — {u['joined_at'][:10]}"
        )
    await query.edit_message_text("\n".join(lines), parse_mode="Markdown")


async def show_all_bets(query):
    bets = db.get_all_bets()
    if not bets:
        await query.edit_message_text("📭 No bets found.")
        return

    lines = [f"🗳️ *All Bets ({len(bets)}):*\n"]
    for b in bets[:20]:
        candidate = CANDIDATES.get(b["candidate"], {}).get("name", b["candidate"])
        lines.append(
            f"• {b.get('username','N/A')} — {candidate} — "
            f"${b['amount_usd']:.2f} → ${b['potential_win']:.2f} — {b['created_at'][:10]}"
        )
    await query.edit_message_text("\n".join(lines), parse_mode="Markdown")
