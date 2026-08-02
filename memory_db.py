"""
SQLite Memory & User Authentication Database for AI Companion App.
Handles Users (Login/Signup), Companion Personas, Chat History, and Memories.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "companion_memory.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes tables for users, chat history, and user profile memory."""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Chat History Table (with user_id and companion_id)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            companion_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. User Memory Table (keyed per user and companion)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, key)
        )
    """)

    conn.commit()
    conn.close()


# --- AUTHENTICATION HELPERS ---

def register_user(username: str, password: str, display_name: str = None) -> dict:
    """Registers a new user."""
    username = username.strip().lower()
    if not username or not password:
        return {"success": False, "error": "Username and password required"}

    password_hash = generate_password_hash(password)
    display_name = display_name or username.capitalize()

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
            (username, password_hash, display_name)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {
            "success": True,
            "user": {"id": user_id, "username": username, "display_name": display_name}
        }
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "error": "Username already exists. Please login."}


def authenticate_user(username: str, password: str) -> dict:
    """Authenticates a user by username and password."""
    username = username.strip().lower()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash, display_name FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        return {
            "success": True,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "display_name": user["display_name"]
            }
        }
    return {"success": False, "error": "Invalid username or password"}


# --- CHAT & MEMORY HELPERS ---

def save_message(user_id: int, companion_id: str, role: str, content: str):
    """Saves a message bound to a user and companion."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (user_id, companion_id, role, content) VALUES (?, ?, ?, ?)",
        (user_id, companion_id, role, content)
    )
    conn.commit()
    conn.close()


def get_recent_history(user_id: int, companion_id: str, limit: int = 14):
    """Retrieves recent chat history for a specific user and companion."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT role, content FROM chat_history 
           WHERE (user_id = ? OR user_id IS NULL) AND companion_id = ? 
           ORDER BY id DESC LIMIT ?""",
        (user_id, companion_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()

    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def clear_history(user_id: int, companion_id: str):
    """Clears history for a specific user and companion."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE (user_id = ? OR user_id IS NULL) AND companion_id = ?", (user_id, companion_id))
    conn.commit()
    conn.close()


def set_memory_fact(user_id: int, key: str, value: str):
    """Stores a remembered fact for a user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_memory (user_id, key, value, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    """, (user_id, key, value))
    conn.commit()
    conn.close()


def get_all_memories(user_id: int):
    """Retrieves remembered facts for a user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM user_memory WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}


# Auto-init DB
init_db()
