"""
SQLite Memory & Context Management Database for AI Companion App.
Stores conversation history, user preferences, and personal memory snippets.
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "companion_memory.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes tables for conversation history and user profile memory."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_memory (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_message(session_id: str, role: str, content: str):
    """Saves a single message to history."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content)
    )
    conn.commit()
    conn.close()


def get_recent_history(session_id: str, limit: int = 12):
    """Retrieves recent conversation history for prompt context."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY id DESC LIMIT ?",
        (session_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()

    # Return in chronological order
    history = [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]
    return history


def clear_history(session_id: str):
    """Clears history for a session."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def set_memory_fact(key: str, value: str):
    """Sets a remembered fact about the user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_memory (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    """, (key, value))
    conn.commit()
    conn.close()


def get_all_memories():
    """Gets all stored memories about the user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM user_memory")
    rows = cursor.fetchall()
    conn.close()

    return {row["key"]: row["value"] for row in rows}


# Auto-initialize DB on import
init_db()
