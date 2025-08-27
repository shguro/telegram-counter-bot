import os
import sqlite3
import types
from contextlib import closing

import pytest

# We import from the app package
from app import bot as bot_module


def test_init_db_creates_table(tmp_path, monkeypatch):
    db_file = tmp_path / "entries.db"
    monkeypatch.setenv("DB_PATH", str(db_file))

    # Re-import to pick up new env var (or patch global)
    bot_module.DB_PATH = str(db_file)

    bot_module.init_db()

    assert db_file.exists(), "DB file should be created"
    with closing(sqlite3.connect(db_file)) as conn, closing(conn.cursor()) as cur:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries'")
        row = cur.fetchone()
        assert row is not None, "entries table should exist"


def test_build_list_and_keyboard_empty(tmp_path, monkeypatch):
    db_file = tmp_path / "entries.db"
    monkeypatch.setenv("DB_PATH", str(db_file))
    bot_module.DB_PATH = str(db_file)
    bot_module.init_db()

    text, keyboard = bot_module.build_list_and_keyboard(chat_id=123)
    assert "No entries" in text
    assert keyboard is None


def test_add_and_increment(tmp_path, monkeypatch):
    db_file = tmp_path / "entries.db"
    monkeypatch.setenv("DB_PATH", str(db_file))
    bot_module.DB_PATH = str(db_file)
    bot_module.init_db()

    # Insert one entry manually
    with closing(bot_module.get_conn()) as conn, closing(conn.cursor()) as cur:
        cur.execute("INSERT INTO entries (chat_id, name, count) VALUES (?, ?, ?)", (5, 'apple', 0))
        conn.commit()

    text, keyboard = bot_module.build_list_and_keyboard(chat_id=5)
    assert 'apple: 0' in text
    assert keyboard is not None

    # Simulate increment via DB (mimicking button handler logic)
    with closing(bot_module.get_conn()) as conn, closing(conn.cursor()) as cur:
        cur.execute("SELECT id, count FROM entries WHERE chat_id=? AND name=?", (5, 'apple'))
        row = cur.fetchone()
        assert row is not None
        entry_id, count = row
        cur.execute("UPDATE entries SET count=? WHERE id=?", (count + 1, entry_id))
        conn.commit()

    text2, _ = bot_module.build_list_and_keyboard(chat_id=5)
    assert 'apple: 1' in text2
