import sqlite3
import uuid
from datetime import datetime
from config import DATABASE_URL


def get_connection():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            full_name   TEXT,
            balance_usd REAL DEFAULT 0.0,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            joined_at   TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Deposits table
    c.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id          TEXT PRIMARY KEY,
            user_id     INTEGER,
            amount_usd  REAL,
            method      TEXT,
            tx_hash     TEXT,
            status      TEXT DEFAULT 'pending',
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            confirmed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # Bets table
    c.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id          TEXT PRIMARY KEY,
            user_id     INTEGER,
            candidate   TEXT,
            amount_usd  REAL,
            multiplier  REAL,
            potential_win REAL,
            status      TEXT DEFAULT 'active',
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # Referral bonuses table
    c.execute("""
        CREATE TABLE IF NOT EXISTS referral_bonuses (
            id          TEXT PRIMARY KEY,
            referrer_id INTEGER,
            referred_id INTEGER,
            bonus_usd   REAL,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (referrer_id) REFERENCES users(user_id),
            FOREIGN KEY (referred_id) REFERENCES users(user_id)
        )
    """)

    # Wallets config table
    c.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            method  TEXT PRIMARY KEY,
            address TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully.")


# ─── User helpers ────────────────────────────────────────────────────────────

def get_or_create_user(user_id: int, username: str, full_name: str, referred_by_code: str = None) -> dict:
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()

    if not user:
        referral_code = str(uuid.uuid4())[:8].upper()
        referred_by = None

        if referred_by_code:
            c.execute("SELECT user_id FROM users WHERE referral_code = ?", (referred_by_code,))
            ref_row = c.fetchone()
            if ref_row and ref_row["user_id"] != user_id:
                referred_by = ref_row["user_id"]

        c.execute("""
            INSERT INTO users (user_id, username, full_name, referral_code, referred_by)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, full_name, referral_code, referred_by))
        conn.commit()

        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()

    conn.close()
    return dict(user)


def get_user(user_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None


def update_balance(user_id: int, amount: float):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET balance_usd = balance_usd + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY joined_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Deposit helpers ──────────────────────────────────────────────────────────

def create_deposit(user_id: int, amount_usd: float, method: str, tx_hash: str) -> str:
    conn = get_connection()
    c = conn.cursor()
    deposit_id = str(uuid.uuid4())[:12].upper()
    c.execute("""
        INSERT INTO deposits (id, user_id, amount_usd, method, tx_hash)
        VALUES (?, ?, ?, ?, ?)
    """, (deposit_id, user_id, amount_usd, method, tx_hash))
    conn.commit()
    conn.close()
    return deposit_id


def get_pending_deposits():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT d.*, u.username, u.full_name
        FROM deposits d
        JOIN users u ON d.user_id = u.user_id
        WHERE d.status = 'pending'
        ORDER BY d.created_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_deposits():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT d.*, u.username, u.full_name
        FROM deposits d
        JOIN users u ON d.user_id = u.user_id
        ORDER BY d.created_at DESC
        LIMIT 100
    """)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def confirm_deposit(deposit_id: str, from_config=False):
    """Confirm a deposit: credit user balance and optionally pay referral bonus."""
    from config import REFERRAL_BONUS_PERCENT
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM deposits WHERE id = ?", (deposit_id,))
    deposit = c.fetchone()
    if not deposit or deposit["status"] != "pending":
        conn.close()
        return False, "Deposit not found or already processed."

    deposit = dict(deposit)

    # Credit user
    c.execute("UPDATE users SET balance_usd = balance_usd + ? WHERE user_id = ?",
              (deposit["amount_usd"], deposit["user_id"]))

    # Mark deposit confirmed
    c.execute("""
        UPDATE deposits SET status = 'confirmed', confirmed_at = ?
        WHERE id = ?
    """, (datetime.utcnow().isoformat(), deposit_id))

    # Pay referral bonus to referrer (first deposit only)
    c.execute("SELECT referred_by FROM users WHERE user_id = ?", (deposit["user_id"],))
    user_row = c.fetchone()
    referrer_id = user_row["referred_by"] if user_row else None

    bonus_paid = 0.0
    if referrer_id:
        # Check if this user had a prior confirmed deposit
        c.execute("""
            SELECT COUNT(*) as cnt FROM deposits
            WHERE user_id = ? AND status = 'confirmed' AND id != ?
        """, (deposit["user_id"], deposit_id))
        prior = c.fetchone()["cnt"]
        if prior == 0:
            bonus = round(deposit["amount_usd"] * REFERRAL_BONUS_PERCENT / 100, 4)
            c.execute("UPDATE users SET balance_usd = balance_usd + ? WHERE user_id = ?",
                      (bonus, referrer_id))
            bonus_id = str(uuid.uuid4())[:12].upper()
            c.execute("""
                INSERT INTO referral_bonuses (id, referrer_id, referred_id, bonus_usd)
                VALUES (?, ?, ?, ?)
            """, (bonus_id, referrer_id, deposit["user_id"], bonus))
            bonus_paid = bonus

    conn.commit()
    conn.close()
    return True, {"deposit": deposit, "referrer_id": referrer_id, "bonus_paid": bonus_paid}


def reject_deposit(deposit_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE deposits SET status = 'rejected' WHERE id = ? AND status = 'pending'",
              (deposit_id,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_user_deposits(user_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM deposits WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Bet helpers ──────────────────────────────────────────────────────────────

def place_bet(user_id: int, candidate: str, amount_usd: float, multiplier: float) -> tuple:
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT balance_usd FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row or row["balance_usd"] < amount_usd:
        conn.close()
        return False, "Insufficient balance."

    potential_win = round(amount_usd * multiplier, 4)
    bet_id = str(uuid.uuid4())[:12].upper()

    c.execute("UPDATE users SET balance_usd = balance_usd - ? WHERE user_id = ?",
              (amount_usd, user_id))
    c.execute("""
        INSERT INTO bets (id, user_id, candidate, amount_usd, multiplier, potential_win)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (bet_id, user_id, candidate, amount_usd, multiplier, potential_win))

    conn.commit()
    conn.close()
    return True, bet_id


def get_user_bets(user_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM bets WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_bets():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT b.*, u.username, u.full_name
        FROM bets b
        JOIN users u ON b.user_id = u.user_id
        ORDER BY b.created_at DESC
        LIMIT 200
    """)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_bet_stats():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT candidate, COUNT(*) as total_bets, SUM(amount_usd) as total_staked
        FROM bets WHERE status = 'active'
        GROUP BY candidate
    """)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Referral helpers ─────────────────────────────────────────────────────────

def get_referral_stats(user_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as total FROM users WHERE referred_by = ?", (user_id,))
    total_referrals = c.fetchone()["total"]
    c.execute("SELECT COALESCE(SUM(bonus_usd), 0) as total FROM referral_bonuses WHERE referrer_id = ?",
              (user_id,))
    total_earned = c.fetchone()["total"]
    conn.close()
    return {"total_referrals": total_referrals, "total_earned": total_earned}


# ─── Wallet helpers ───────────────────────────────────────────────────────────

def get_wallets():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM wallets")
    rows = c.fetchall()
    conn.close()
    return {r["method"]: r["address"] for r in rows}


def set_wallet(method: str, address: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO wallets (method, address, updated_at) VALUES (?, ?, ?)
        ON CONFLICT(method) DO UPDATE SET address = excluded.address, updated_at = excluded.updated_at
    """, (method, address, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


# ─── Stats helpers ────────────────────────────────────────────────────────────

def get_platform_stats():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM users")
    total_users = c.fetchone()["cnt"]
    c.execute("SELECT COUNT(*) as cnt FROM deposits WHERE status = 'confirmed'")
    total_deposits = c.fetchone()["cnt"]
    c.execute("SELECT COALESCE(SUM(amount_usd),0) as total FROM deposits WHERE status = 'confirmed'")
    total_deposited = c.fetchone()["total"]
    c.execute("SELECT COUNT(*) as cnt FROM bets WHERE status = 'active'")
    total_bets = c.fetchone()["cnt"]
    c.execute("SELECT COALESCE(SUM(amount_usd),0) as total FROM bets WHERE status = 'active'")
    total_staked = c.fetchone()["total"]
    conn.close()
    return {
        "total_users": total_users,
        "total_deposits": total_deposits,
        "total_deposited": total_deposited,
        "total_bets": total_bets,
        "total_staked": total_staked,
    }
