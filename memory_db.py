"""
SQLite Memory & User Authentication Database for AI Companion App.
Handles Users (Login/Signup), Companion Personas, Chat History, and Memories.
Includes robust schema compatibility for session_id, user_id, and companion_id.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "companion_memory.db")


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes and migrates tables for users, chat history, and user profile memory."""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migrate: add email column if not exists
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [row["name"] for row in cursor.fetchall()]
    if "email" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")

    # 2. Chat History Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT DEFAULT 'default_session',
            user_id INTEGER,
            companion_id TEXT DEFAULT 'ananya',
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Check and migrate columns if old schema exists
    cursor.execute("PRAGMA table_info(chat_history)")
    columns = [row["name"] for row in cursor.fetchall()]
    
    if "user_id" not in columns:
        cursor.execute("ALTER TABLE chat_history ADD COLUMN user_id INTEGER")
    if "companion_id" not in columns:
        cursor.execute("ALTER TABLE chat_history ADD COLUMN companion_id TEXT DEFAULT 'ananya'")
    if "session_id" not in columns:
        cursor.execute("ALTER TABLE chat_history ADD COLUMN session_id TEXT DEFAULT 'default_session'")

    # 3. User Memory Table
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

def register_user(username: str, password: str, display_name: str = None, email: str = None) -> dict:
    username = username.strip().lower()
    email = email.strip().lower() if email else None
    if not username or not password:
        return {"success": False, "error": "Username and password required"}
    if not email:
        return {"success": False, "error": "Email is required"}

    password_hash = generate_password_hash(password)
    display_name = display_name or username.capitalize()

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, display_name) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, display_name)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {
            "success": True,
            "user": {"id": user_id, "username": username, "email": email, "display_name": display_name}
        }
    except sqlite3.IntegrityError as e:
        conn.close()
        if "email" in str(e):
            return {"success": False, "error": "Email already registered. Please login."}
        return {"success": False, "error": "Username already exists. Please login."}


def authenticate_user(login_id: str, password: str) -> dict:
    """Login via email OR username."""
    login_id = login_id.strip().lower()
    conn = get_db()
    cursor = conn.cursor()
    # Try email first, then username
    cursor.execute(
        "SELECT id, username, email, password_hash, display_name FROM users WHERE email = ? OR username = ?",
        (login_id, login_id)
    )
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        return {
            "success": True,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "display_name": user["display_name"]
            }
        }
    return {"success": False, "error": "Invalid email/username or password"}


# --- CHAT & MEMORY HELPERS ---

def save_message(user_id: int, companion_id: str, role: str, content: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (session_id, user_id, companion_id, role, content) VALUES (?, ?, ?, ?, ?)",
        ("default_session", user_id, companion_id or 'ananya', role, content)
    )
    conn.commit()
    conn.close()


def get_recent_history(user_id: int, companion_id: str, limit: int = 14):
    conn = get_db()
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute(
            """SELECT role, content FROM chat_history 
               WHERE user_id = ? AND companion_id = ? 
               ORDER BY id DESC LIMIT ?""",
            (user_id, companion_id or 'ananya', limit)
        )
    else:
        cursor.execute(
            """SELECT role, content FROM chat_history 
               WHERE (user_id IS NULL OR user_id = 0) AND companion_id = ? 
               ORDER BY id DESC LIMIT ?""",
            (companion_id or 'ananya', limit)
        )
        
    rows = cursor.fetchall()
    conn.close()

    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def clear_history(user_id: int, companion_id: str):
    conn = get_db()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("DELETE FROM chat_history WHERE user_id = ? AND companion_id = ?", (user_id, companion_id or 'ananya'))
    else:
        cursor.execute("DELETE FROM chat_history WHERE (user_id IS NULL OR user_id = 0) AND companion_id = ?", (companion_id or 'ananya',))
    conn.commit()
    conn.close()


def set_memory_fact(user_id: int, key: str, value: str):
    if not user_id:
        return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_memory (user_id, key, value, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    """, (user_id, key, value))
    conn.commit()
    conn.close()


def get_all_memories(user_id: int):
    if not user_id:
        return {}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM user_memory WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}


# Auto-init DB
init_db()
