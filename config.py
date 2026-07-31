import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = "naija2027election_bot"


# Admin Configuration
def _parse_admin_ids(raw: str) -> list:
    ids = []
    for part in raw.split(","):
        # Strip any non-digit prefix like "User ID: " and whitespace
        digits = "".join(c for c in part if c.isdigit())
        if digits:
            ids.append(int(digits))
    return ids


ADMIN_IDS = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

# Database (using SQLITE_DB_PATH to avoid conflict with Replit's managed DATABASE_URL)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.getenv("SQLITE_DB_PATH", os.path.join(_BASE_DIR, "betting_bot.db"))

# Candidates and Multipliers
CANDIDATES = {
    "tinubu": {"name": "Bola Tinubu (APC)", "multiplier": 70},
    "adc": {"name": "Atiku Abubakar (ADC)", "multiplier": 50},
    "obi": {"name": "Peter Obi (NDC)", "multiplier": 40},
}

# Betting Configuration
MIN_DEPOSIT_USD = 13  # Minimum deposit in USD
REFERRAL_BONUS_PERCENT = 5  # 5% referral bonus

# Payment Wallets (managed by admin)
USDT_TRC20_WALLET = os.getenv("USDT_TRC20_WALLET", "")
SOLANA_WALLET = os.getenv("SOLANA_WALLET", "")

# App Configuration
PORT = int(os.getenv("PORT", 8080))

# Messages
WELCOME_MESSAGE = """
🇳🇬 *Welcome to Naija 2027 Election Betting Bot* 🇳🇬

Bet on who will win the 2027 Nigerian Presidential Election!

*Candidates & Multipliers:*
🔵 Bola Tinubu (APC) — 70x
🟢 Atiku Abubakar (ADC) — 50x
🔴 Peter Obi (NDC) — 40x

*Minimum Deposit:* $13 USDT

Use /help to see all commands.
Use /bet to place your bet.
Use /deposit to fund your account.
Use /balance to check your balance.
Use /referral to get your referral link.
"""

HELP_MESSAGE = """
*📋 Available Commands:*

/start — Welcome message
/bet — Place a bet on a candidate
/deposit — Fund your account (USDT TRC20 or Solana)
/balance — Check your account balance
/referral — Get your referral link & stats
/mybets — View your betting history
/help — Show this help message

*💰 Payment Methods:*
• USDT (TRC20 Network)
• Solana (SOL)

*📌 Rules:*
• Minimum deposit: $13 USD
• 5% bonus for every referral who deposits
• Winnings paid after election results
"""
