
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 🔥 TEST - Remove this after testing
    await update.message.reply_text("🔥 /deposit command is WORKING!")
    return  # ← This will stop the function here for testing

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from config import (
    CANDIDATES,
    MIN_DEPOSIT_USD,
    BOT_USERNAME,
    WELCOME_MESSAGE,
    HELP_MESSAGE,
)

# Conversation states
CHOOSE_CANDIDATE, ENTER_BET_AMOUNT = range(2)
CHOOSE_PAYMENT, ENTER_TX_HASH, ENTER_AMOUNT = range(3)
WITHDRAW_METHOD, WITHDRAW_ADDRESS, WITHDRAW_AMOUNT = range(3)


# ─── /start ──────────────────────────────────────────────────────────────────


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    ref_code = args[0] if args else None

    db_user = db.get_or_create_user(
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name or "",
        referred_by_code=ref_code,
    )

    keyboard = [
        [
            InlineKeyboardButton("🎯 Place a Bet", callback_data="menu_bet"),
            InlineKeyboardButton("💰 Deposit", callback_data="menu_deposit"),
        ],
        [
            InlineKeyboardButton("💼 My Balance", callback_data="menu_balance"),
            InlineKeyboardButton("📊 My Bets", callback_data="menu_mybets"),
        ],
        [
            InlineKeyboardButton("💸 Withdraw", callback_data="menu_withdraw"),
            InlineKeyboardButton("👥 Referral", callback_data="menu_referral"),
        ],
        [InlineKeyboardButton("❓ Help", callback_data="menu_help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        WELCOME_MESSAGE, parse_mode="Markdown", reply_markup=reply_markup
    )


# ─── /help ───────────────────────────────────────────────────────────────────


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_MESSAGE, parse_mode="Markdown")


# ─── /balance ────────────────────────────────────────────────────────────────


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = db.get_user(user.id)
    if not db_user:
        db.get_or_create_user(user.id, user.username or "", user.full_name or "")
        db_user = db.get_user(user.id)

    msg = (
        f"💼 *Your Account Balance*\n\n"
        f"👤 Name: {db_user['full_name']}\n"
        f"💵 Balance: *${db_user['balance_usd']:.2f} USD*\n"
        f"🔑 Referral Code: `{db_user['referral_code']}`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ─── /deposit ────────────────────────────────────────────────────────────────


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username or "", user.full_name or "")
    wallets = db.get_wallets()

    usdt_wallet = wallets.get("USDT_TRC20", "Not set — contact admin")
    sol_wallet = wallets.get("SOLANA", "Not set — contact admin")

    msg = (
        f"💰 *Fund Your Account*\n\n"
        f"Minimum deposit: *${MIN_DEPOSIT_USD} USD*\n\n"
        f"*USDT (TRC20):*\n`{usdt_wallet}`\n\n"
        f"*Solana (SOL):*\n`{sol_wallet}`\n\n"
        f"After sending, use /confirm_deposit to submit your transaction hash.\n\n"
        f"ℹ️ Deposits are confirmed manually by admin within 30 minutes."
    )
    keyboard = [
        [InlineKeyboardButton("✅ Submit TX Hash", callback_data="deposit_submit")]
    ]
    await update.message.reply_text(
        msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── /confirm_deposit ────────────────────────────────────────────────────────


async def confirm_deposit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("USDT TRC20", callback_data="pay_USDT_TRC20"),
            InlineKeyboardButton("Solana", callback_data="pay_SOLANA"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ]
    await update.message.reply_text(
        "📩 *Submit Deposit*\n\nSelect payment method:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSE_PAYMENT


async def deposit_choose_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.replace("pay_", "")
    context.user_data["deposit_method"] = method
    await query.edit_message_text(
        f"💵 *Enter deposit amount in USD:*\n\n(Minimum: ${MIN_DEPOSIT_USD})",
        parse_mode="Markdown",
    )
    return ENTER_AMOUNT


async def deposit_enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number.")
        return ENTER_AMOUNT

    if amount < MIN_DEPOSIT_USD:
        await update.message.reply_text(
            f"❌ Minimum deposit is ${MIN_DEPOSIT_USD}. Please enter a higher amount."
        )
        return ENTER_AMOUNT

    context.user_data["deposit_amount"] = amount
    await update.message.reply_text(
        "🔗 *Enter your transaction hash (TX ID):*", parse_mode="Markdown"
    )
    return ENTER_TX_HASH


async def deposit_enter_tx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tx_hash = update.message.text.strip()
    method = context.user_data.get("deposit_method", "UNKNOWN")
    amount = context.user_data.get("deposit_amount", 0)

    deposit_id = db.create_deposit(user.id, amount, method, tx_hash)

    msg = (
        f"✅ *Deposit Submitted!*\n\n"
        f"📋 Deposit ID: `{deposit_id}`\n"
        f"💵 Amount: ${amount:.2f} USD\n"
        f"💳 Method: {method}\n"
        f"🔗 TX Hash: `{tx_hash}`\n\n"
        f"⏳ Admin will verify and confirm within 30 minutes."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

    # Notify admins
    from config import ADMIN_IDS

    admin_msg = (
        f"🔔 *New Deposit Request*\n\n"
        f"👤 User: {user.full_name} (@{user.username})\n"
        f"🆔 User ID: `{user.id}`\n"
        f"📋 Deposit ID: `{deposit_id}`\n"
        f"💵 Amount: ${amount:.2f} USD\n"
        f"💳 Method: {method}\n"
        f"🔗 TX: `{tx_hash}`\n\n"
        f"Use /admin → Pending Deposits to confirm or reject."
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, admin_msg, parse_mode="Markdown")
        except Exception:
            pass

    context.user_data.clear()
    return ConversationHandler.END


# ─── /bet ────────────────────────────────────────────────────────────────────


async def bet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = db.get_or_create_user(user.id, user.username or "", user.full_name or "")

    if db_user["balance_usd"] <= 0:
        await update.message.reply_text(
            "❌ You have no balance. Please /deposit first.", parse_mode="Markdown"
        )
        return ConversationHandler.END

    keyboard = []
    for key, info in CANDIDATES.items():
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{info['name']} ({info['multiplier']}x)",
                    callback_data=f"bet_{key}",
                )
            ]
        )
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])

    await update.message.reply_text(
        f"🎯 *Place Your Bet*\n\n"
        f"💵 Your balance: *${db_user['balance_usd']:.2f} USD*\n\n"
        f"Select a candidate:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSE_CANDIDATE


async def bet_choose_candidate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    candidate_key = query.data.replace("bet_", "")
    candidate = CANDIDATES.get(candidate_key)
    if not candidate:
        await query.edit_message_text("❌ Invalid candidate.")
        return ConversationHandler.END

    context.user_data["bet_candidate"] = candidate_key
    context.user_data["bet_multiplier"] = candidate["multiplier"]

    user = query.from_user
    db_user = db.get_user(user.id)

    await query.edit_message_text(
        f"✅ You selected: *{candidate['name']}* ({candidate['multiplier']}x)\n\n"
        f"💵 Your balance: *${db_user['balance_usd']:.2f} USD*\n\n"
        f"Enter bet amount in USD (min ${MIN_DEPOSIT_USD}):",
        parse_mode="Markdown",
    )
    return ENTER_BET_AMOUNT


async def bet_enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number.")
        return ENTER_BET_AMOUNT

    if amount < MIN_DEPOSIT_USD:
        await update.message.reply_text(f"❌ Minimum bet is ${MIN_DEPOSIT_USD}.")
        return ENTER_BET_AMOUNT

    candidate_key = context.user_data.get("bet_candidate")
    multiplier = context.user_data.get("bet_multiplier")
    candidate = CANDIDATES[candidate_key]

    db_user = db.get_user(user.id)
    if db_user["balance_usd"] < amount:
        await update.message.reply_text(
            f"❌ Insufficient balance. You have ${db_user['balance_usd']:.2f} USD."
        )
        return ENTER_BET_AMOUNT

    potential_win = round(amount * multiplier, 2)

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm Bet", callback_data="confirm_bet"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_bet"),
        ]
    ]
    context.user_data["bet_amount"] = amount

    await update.message.reply_text(
        f"🎯 *Confirm Your Bet*\n\n"
        f"Candidate: *{candidate['name']}*\n"
        f"Amount: *${amount:.2f} USD*\n"
        f"Multiplier: *{multiplier}x*\n"
        f"Potential Win: *${potential_win:.2f} USD*\n\n"
        f"Confirm?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ENTER_BET_AMOUNT


async def bet_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    candidate_key = context.user_data.get("bet_candidate")
    multiplier = context.user_data.get("bet_multiplier")
    amount = context.user_data.get("bet_amount")

    success, result = db.place_bet(user.id, candidate_key, amount, multiplier)
    if success:
        potential_win = round(amount * multiplier, 2)
        await query.edit_message_text(
            f"🎉 *Bet Placed Successfully!*\n\n"
            f"📋 Bet ID: `{result}`\n"
            f"🗳️ Candidate: *{CANDIDATES[candidate_key]['name']}*\n"
            f"💵 Amount: *${amount:.2f} USD*\n"
            f"🏆 Potential Win: *${potential_win:.2f} USD*\n\n"
            f"Good luck! 🇳🇬",
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text(f"❌ Bet failed: {result}")

    context.user_data.clear()
    return ConversationHandler.END


async def bet_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("❌ Bet cancelled.")
    return ConversationHandler.END


# ─── /mybets ─────────────────────────────────────────────────────────────────


async def mybets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bets = db.get_user_bets(user.id)

    if not bets:
        await update.message.reply_text(
            "📭 You have no bets yet. Use /bet to place one!"
        )
        return

    lines = ["📊 *Your Bets:*\n"]
    for b in bets[:10]:
        candidate = CANDIDATES.get(b["candidate"], {}).get("name", b["candidate"])
        status_emoji = {"active": "🟡", "won": "🏆", "lost": "❌"}.get(
            b["status"], "⚪"
        )
        lines.append(
            f"{status_emoji} {candidate}\n"
            f"   💵 ${b['amount_usd']:.2f} → 🏆 ${b['potential_win']:.2f}\n"
            f"   📅 {b['created_at'][:10]}\n"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ─── /referral ────────────────────────────────────────────────────────────────


async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = db.get_or_create_user(user.id, user.username or "", user.full_name or "")
    stats = db.get_referral_stats(user.id)

    ref_link = f"https://t.me/{BOT_USERNAME}?start={db_user['referral_code']}"
    msg = (
        f"👥 *Your Referral Program*\n\n"
        f"🔗 Your referral link:\n`{ref_link}`\n\n"
        f"📊 Stats:\n"
        f"• Total referrals: *{stats['total_referrals']}*\n"
        f"• Total bonuses earned: *${stats['total_earned']:.2f} USD*\n\n"
        f"💡 Earn *5%* of every deposit made by users who join via your link!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ─── /wallet ─────────────────────────────────────────────────────────────────


async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username or "", user.full_name or "")

    if not context.args:
        db_user = db.get_user(user.id)
        current = db_user.get("withdrawal_address") or "Not set"
        await update.message.reply_text(
            f"💳 *Your Withdrawal Address*\n\n"
            f"Current: `{current}`\n\n"
            f"To update, use:\n`/wallet <your_address>`\n\n"
            f"Example:\n`/wallet TYourTRC20AddressHere`",
            parse_mode="Markdown",
        )
        return

    address = context.args[0].strip()
    if len(address) < 20:
        await update.message.reply_text(
            "❌ That address looks too short. Please check and try again."
        )
        return

    db.set_withdrawal_address(user.id, address)
    await update.message.reply_text(
        f"✅ *Withdrawal address saved!*\n\n`{address}`\n\n"
        f"You can now use /withdraw to request a withdrawal.",
        parse_mode="Markdown",
    )


# ─── /withdraw ────────────────────────────────────────────────────────────────


async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = db.get_or_create_user(user.id, user.username or "", user.full_name or "")

    # Handle both command and callback
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        reply = query.edit_message_text
        user_id = query.from_user.id
    else:
        reply = update.message.reply_text
        user_id = update.effective_user.id

    if db_user["balance_usd"] <= 0:
        await reply("❌ Your balance is $0.00. Nothing to withdraw.")
        return ConversationHandler.END

    if not db_user.get("withdrawal_address"):
        await reply(
            "⚠️ You haven't set a withdrawal address yet.\n\n"
            "Use `/wallet <your_address>` first, then try /withdraw again.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton("USDT TRC20", callback_data="wd_USDT_TRC20"),
            InlineKeyboardButton("Solana", callback_data="wd_SOLANA"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ]
    await reply(
        f"💸 *Withdrawal Request*\n\n"
        f"💵 Available balance: *${db_user['balance_usd']:.2f} USD*\n"
        f"📬 Address: `{db_user['withdrawal_address']}`\n\n"
        f"Select withdrawal method:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return WITHDRAW_METHOD


async def withdraw_choose_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.replace("wd_", "")
    context.user_data["wd_method"] = method

    user = query.from_user
    db_user = db.get_user(user.id)

    await query.edit_message_text(
        f"💸 *Withdrawal — {method}*\n\n"
        f"💵 Available balance: *${db_user['balance_usd']:.2f} USD*\n\n"
        f"Enter the amount in USD you want to withdraw:",
        parse_mode="Markdown",
    )
    return WITHDRAW_AMOUNT


async def withdraw_enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number.")
        return WITHDRAW_AMOUNT

    if amount <= 0:
        await update.message.reply_text("❌ Amount must be greater than $0.")
        return WITHDRAW_AMOUNT

    db_user = db.get_user(user.id)
    if amount > db_user["balance_usd"]:
        await update.message.reply_text(
            f"❌ Insufficient balance.\n"
            f"Your balance: *${db_user['balance_usd']:.2f} USD*\n"
            f"Requested: *${amount:.2f} USD*",
            parse_mode="Markdown",
        )
        return WITHDRAW_AMOUNT

    method = context.user_data.get("wd_method", "USDT_TRC20")
    address = db_user.get("withdrawal_address", "")
    context.user_data["wd_amount"] = amount

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data="confirm_wd"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_wd"),
        ]
    ]
    await update.message.reply_text(
        f"💸 *Confirm Withdrawal*\n\n"
        f"💵 Amount: *${amount:.2f} USD*\n"
        f"💳 Method: *{method}*\n"
        f"📬 Address: `{address}`\n\n"
        f"Confirm?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return WITHDRAW_AMOUNT


async def withdraw_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    amount = context.user_data.get("wd_amount")
    method = context.user_data.get("wd_method", "USDT_TRC20")
    db_user = db.get_user(user.id)
    address = db_user.get("withdrawal_address", "")

    success, result = db.create_withdrawal(user.id, amount, method, address)
    if not success:
        await query.edit_message_text(f"❌ Withdrawal failed: {result}")
        context.user_data.clear()
        return ConversationHandler.END

    await query.edit_message_text(
        f"✅ *Withdrawal Requested!*\n\n"
        f"📋 ID: `{result}`\n"
        f"💵 Amount: *${amount:.2f} USD*\n"
        f"💳 Method: *{method}*\n"
        f"📬 Address: `{address}`\n\n"
        f"⏳ Admin will process your withdrawal shortly. You'll be notified when done.",
        parse_mode="Markdown",
    )

    # Notify admins
    from config import ADMIN_IDS

    admin_msg = (
        f"🔔 *New Withdrawal Request*\n\n"
        f"👤 User: {user.full_name} (@{user.username})\n"
        f"🆔 User ID: `{user.id}`\n"
        f"📋 Withdrawal ID: `{result}`\n"
        f"💵 Amount: ${amount:.2f} USD\n"
        f"💳 Method: {method}\n"
        f"📬 Address: `{address}`\n\n"
        f"Use /approve `{result}` or /reject `{result}`"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, admin_msg, parse_mode="Markdown")
        except Exception:
            pass

    context.user_data.clear()
    return ConversationHandler.END


async def withdraw_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("❌ Withdrawal cancelled.")
    return ConversationHandler.END


# ─── /mywithdrawals ───────────────────────────────────────────────────────────


async def mywithdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    withdrawals = db.get_user_withdrawals(user.id)

    if not withdrawals:
        await update.message.reply_text(
            "📭 You have no withdrawal requests yet. Use /withdraw to request one."
        )
        return

    lines = ["💸 *Your Withdrawals:*\n"]
    for w in withdrawals[:10]:
        emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(
            w["status"], "⚪"
        )
        lines.append(
            f"{emoji} `{w['id']}` — ${w['amount_usd']:.2f} — {w['method']}\n"
            f"   📅 {w['created_at'][:10]}  Status: *{w['status']}*\n"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ─── Callback query router ────────────────────────────────────────────────────


async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_bet":
        await query.message.reply_text("Use /bet to place a bet.")
    elif data == "menu_deposit":
        await query.message.reply_text("Use /deposit to fund your account.")
    elif data == "menu_balance":
        user = query.from_user
        db_user = db.get_or_create_user(
            user.id, user.username or "", user.full_name or ""
        )
        await query.message.reply_text(
            f"💼 *Balance:* ${db_user['balance_usd']:.2f} USD", parse_mode="Markdown"
        )
    elif data == "menu_mybets":
        await query.message.reply_text("Use /mybets to view your bets.")
    elif data == "menu_referral":
        await query.message.reply_text("Use /referral to get your referral link.")
    elif data == "menu_withdraw":
        await withdraw_start(update, context)
    elif data == "menu_help":
        await query.message.reply_text(HELP_MESSAGE, parse_mode="Markdown")
    elif data == "cancel":
        await query.edit_message_text("❌ Cancelled.")


# ─── Cancel handler ───────────────────────────────────────────────────────────


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END
