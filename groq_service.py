"""
Groq Service Integration for Multi-Gender AI Companions.
Injects gender-specific persona prompts (Girl/Boy) and manages session context.
"""

import os
import random
from dotenv import load_dotenv
from persona_dataset import (
    COMPANION_PERSONAS,
    get_companion_prompt,
    FALLBACK_RESPONSES_GENDER,
    clean_bot_cliches
)
from memory_db import get_recent_history, get_all_memories, save_message

load_dotenv()

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


def get_groq_client(custom_api_key=None):
    api_key = custom_api_key or os.getenv("GROQ_API_KEY")
    if GROQ_AVAILABLE and api_key and api_key.strip():
        try:
            return Groq(api_key=api_key.strip())
        except Exception:
            return None
    return None


def generate_companion_response(user_id: int, companion_id: str, user_message: str, custom_api_key: str = None) -> dict:
    """
    Generates response for a specific user and companion persona.
    """
    companion_id = companion_id if companion_id in COMPANION_PERSONAS else "ananya"
    companion_info = COMPANION_PERSONAS[companion_id]

    # Save user message
    save_message(user_id, companion_id, "user", user_message)

    # Get recent history & memories
    history = get_recent_history(user_id, companion_id, limit=12)
    memories = get_all_memories(user_id) if user_id else {}

    memory_snippet = ""
    if memories:
        items = [f"{k}: {v}" for k, v in memories.items()]
        memory_snippet = f"\n[User Profile Facts Remembered: {', '.join(items)}]"

    # Get system prompt for companion gender/persona
    system_prompt = get_companion_prompt(companion_id) + memory_snippet

    client = get_groq_client(custom_api_key)
    selected_model = "llama-3.3-70b-versatile"

    if client:
        try:
            messages = [{"role": "system", "content": system_prompt}]
            for msg in history:
                role = "assistant" if msg["role"] == "assistant" else "user"
                messages.append({"role": role, "content": msg["content"]})

            chat_completion = client.chat.completions.create(
                messages=messages,
                model=selected_model,
                temperature=0.88,
                max_tokens=350,
                top_p=0.9,
            )

            raw_reply = chat_completion.choices[0].message.content
            cleaned_reply = clean_bot_cliches(raw_reply)

            save_message(user_id, companion_id, "assistant", cleaned_reply)

            return {
                "response": cleaned_reply,
                "source": "groq",
                "model": selected_model
            }

        except Exception as e:
            print(f"Groq API call warning: {e}")

    # Fallback execution
    gender = companion_info["gender"]
    fallback_pool = FALLBACK_RESPONSES_GENDER.get(gender, FALLBACK_RESPONSES_GENDER["female"])
    reply = random.choice(fallback_pool)

    save_message(user_id, companion_id, "assistant", reply)

    return {
        "response": reply,
        "source": "fallback",
        "model": f"{companion_info['name']} Engine"
    }
