import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",")]

# Election Candidates
CANDIDATES = {
    "Tinubu": {
        "name": "Tinubu",
        "multiplier": 70,
        "emoji": "🇳🇬"
    },
    "Atiku": {
        "name": "Atiku",
        "multiplier": 50,
        "emoji": "🇳🇬"
    },
    "Obi": {
        "name": "Obi",
        "multiplier": 40,
        "emoji": "🇳🇬"
    }
}

# Payment Settings
MIN_DEPOSIT_USD = 13
REFERRAL_BONUS_PERCENT = 5  # 5%
BOT_USERNAME = "naija2027election_bot"

# Database
DATABASE_URL = "9ja27_bot.db"

# Messages
WELCOME_MESSAGE = """
🎯 *WELCOME TO NAIJA2027 ELECTION BETTING BOT* 🇳🇬

*🏆 2027 Presidential Election Betting*

*Current Odds:*
🇳🇬 Tinubu: *70x*
🇳🇬 Atiku: *50x*
🇳🇬 Obi: *40x*

━━━━━━━━━━━━━━━━━━━━━

📌 *How It Works:*

1️⃣ Deposit minimum *$13* (USDT TRC20 or Solana)
2️⃣ Choose your preferred candidate
3️⃣ Place your bet and win BIG! 💰

━━━━━━━━━━━━━━━━━━━━━

💰 *Referral Bonus: 5%* for every friend!
✅ *Minimum Bet:* $1
⚡ *Instant Payouts* after election

*Start betting now!* 🚀
"""

HELP_MESSAGE = """
ℹ️ *Help & Guide - 9ja27 Bot*

━━━━━━━━━━━━━━━━━━━━━

📌 *Getting Started:*
1. Click 💰 *Deposit* to fund your account
2. Minimum deposit: *$13 USD*
3. Click 📊 *Place Bet* to wager

━━━━━━━━━━━━━━━━━━━━━

🎯 *Available Candidates:*
• 🇳🇬 Tinubu - *70x*
• 🇳🇬 Atiku - *50x*
• 🇳🇬 Obi - *40x*

━━━━━━━━━━━━━━━━━━━━━

📋 *Rules:*
• Minimum bet: *$1 USD*
• Maximum bet: *No limit*
• Referral bonus: *5%* of deposit
"""
