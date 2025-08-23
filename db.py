# db.py
import os
import sqlite3
from flask import g
from hashlib import sha256
from datetime import date, datetime
from constants import DATABASE_URL, MEMBERS

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_URL, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        _ensure_schema(g.db)
        _migrate_v2(g.db)
    return g.db

def _ensure_schema(db):
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
      update_ts TEXT DEFAULT (CURRENT_TIMESTAMP),
      UNIQUE(day, member_key)
    );
    """)
    # Seed default members
    have = db.execute("SELECT COUNT(*) AS n FROM members").fetchone()["n"]
    if have == 0:
        for k, v in MEMBERS.items():
            db.execute("INSERT OR IGNORE INTO members(key, name, active) VALUES (?,?,1)", (k, v))
    # Seed admin
    have_admin = db.execute("SELECT COUNT(*) AS n FROM users WHERE username='admin'").fetchone()["n"]
    if have_admin == 0:
        db.execute("INSERT OR IGNORE INTO users(username, password_hash, is_admin) VALUES (?,?,1)",
                   ("admin", sha256("change-me".encode()).hexdigest()))
    db.commit()

def _migrate_v2(db):
    # Add columns if missing
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
            SET update_user=COALESCE(update_user,'admin'),
                update_ts=COALESCE(update_ts, CURRENT_TIMESTAMP)
        """)
        db.commit()

def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
