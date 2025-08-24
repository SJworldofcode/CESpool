# db.py
import os
import sqlite3
from flask import g
from hashlib import sha256
from datetime import date, datetime

# ---- DB path resolution (portable + overrideable) ---------------------------
# Project root (folder where this file lives)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data.db")

# Optional env override, else fall back to constants.DATABASE_URL if present,
# else use ./data.db next to this file.
def _resolve_db_path() -> str:
    env_path = os.environ.get("CESPOOL_DB")
    if env_path:
        return os.path.abspath(env_path)

    try:
        # constants is optional; if missing or empty we ignore it
        from constants import DATABASE_URL as CONST_DB_URL  # type: ignore
        if CONST_DB_URL:
            # If it's absolute, use as-is; if relative, anchor to project root
            return os.path.abspath(
                CONST_DB_URL if os.path.isabs(CONST_DB_URL)
                else os.path.join(BASE_DIR, CONST_DB_URL)
            )
    except Exception:
        pass

    return DEFAULT_DB_PATH

DB_PATH = _resolve_db_path()

# ----------------------------------------------------------------------------

def get_db():
    """Get a request-scoped SQLite connection, ensure schema/migrations."""
    if "db" not in g:
        # detect_types enables better DATE/TIMESTAMP handling if you ever add it
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        _ensure_schema(g.db)
        _migrate_v2(g.db)
    return g.db

def _ensure_schema(db: sqlite3.Connection):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      is_admin INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS members (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      key TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS entries (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      day TEXT NOT NULL,
      member_key TEXT NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('D','R','O')),
      update_user TEXT DEFAULT 'admin',
      update_ts   TEXT DEFAULT (CURRENT_TIMESTAMP),
      UNIQUE(day, member_key)
    );
    """)
    # Seed default members
    have = db.execute("SELECT COUNT(*) AS n FROM members").fetchone()["n"]
    if have == 0:
        try:
            from constants import MEMBERS  # lazy import to avoid circulars
        except Exception:
            MEMBERS = {}
        for k, v in MEMBERS.items():
            db.execute(
                "INSERT OR IGNORE INTO members(key, name, active) VALUES (?,?,1)",
                (k, v),
            )
    # Seed admin (only if none exist)
    have_admin = db.execute(
        "SELECT COUNT(*) AS n FROM users WHERE username='admin'"
    ).fetchone()["n"]
    if have_admin == 0:
        db.execute(
            "INSERT OR IGNORE INTO users(username, password_hash, is_admin) VALUES (?,?,1)",
            ("admin", sha256("change-me".encode()).hexdigest()),
        )
    db.commit()

def _migrate_v2(db: sqlite3.Connection):
    """Add columns introduced in v2 if they’re missing."""
    cols = {r["name"] for r in db.execute("PRAGMA table_info(entries)").fetchall()}
    altered = False
    if "update_user" not in cols:
        db.execute("ALTER TABLE entries ADD COLUMN update_user TEXT DEFAULT 'admin'")
        altered = True
    if "update_ts" not in cols:
        db.execute("ALTER TABLE entries ADD COLUMN update_ts TEXT DEFAULT (CURRENT_TIMESTAMP)")
        altered = True
    if altered:
        db.execute("""
            UPDATE entries
            SET update_user = COALESCE(update_user, 'admin'),
                update_ts   = COALESCE(update_ts, CURRENT_TIMESTAMP)
        """)
        db.commit()

def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
