"""
Groq API Integration Engine for AI Companion.
Supports high-speed Llama 3.3 70B & 3.1 8B models with realistic fallback mode.
"""

import os
import random
from dotenv import load_dotenv
from persona_dataset import SYSTEM_PERSONA_PROMPT, FALLBACK_HUMAN_RESPONSES, clean_bot_cliches
from memory_db import get_recent_history, get_all_memories, save_message

load_dotenv()

# Attempt to import groq SDK
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


def get_groq_client(custom_api_key=None):
    """Retrieves Groq client instance using custom key, env var, or None."""
    api_key = custom_api_key or os.getenv("GROQ_API_KEY")
    if GROQ_AVAILABLE and api_key and api_key.strip():
        try:
            return Groq(api_key=api_key.strip())
        except Exception:
            return None
    return None


def detect_mood_category(user_text: str) -> str:
    """Categorizes user sentiment for smart fallback selection."""
    text = user_text.lower()
    if any(w in text for w in ["akela", "akele", "lonely", "alone", "koi nahi", "miss", "sad", "udaas"]):
        return "lonely"
    elif any(w in text for w in ["stress", "tension", "worried", "work", "office", "thak", "tired"]):
        return "stressed"
    elif any(w in text for w in ["raat", "night", "neend", "sleep", "late", "so", "overthink"]):
        return "late_night"
    elif any(w in text for w in ["khush", "happy", "great", "mast", "party", "yay", "haha", "lol"]):
        return "happy"
    return "general"


def generate_companion_response(session_id: str, user_message: str, custom_api_key: str = None) -> dict:
    """
    Main function to get a response from Groq API or Fallback.
    Returns dict: {"response": str, "source": "groq"|"fallback", "model": str}
    """
    # 1. Save user message to memory DB
    save_message(session_id, "user", user_message)

    # 2. Get history and stored facts
    history = get_recent_history(session_id, limit=10)
    memories = get_all_memories()

    # Build memory context snippet
    memory_snippet = ""
    if memories:
        memory_items = [f"{k}: {v}" for k, v in memories.items()]
        memory_snippet = f"\n[User Facts Remembered: {', '.join(memory_items)}]"

    # 3. Check for Groq client
    client = get_groq_client(custom_api_key)
    
    selected_model = "llama-3.3-70b-versatile"

    if client:
        try:
            # Build messages array
            messages = [{"role": "system", "content": SYSTEM_PERSONA_PROMPT + memory_snippet}]

            # Add recent context
            for msg in history:
                role = "assistant" if msg["role"] == "assistant" else "user"
                messages.append({"role": role, "content": msg["content"]})

            # Call Groq API
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=selected_model,
                temperature=0.85,  # High temperature for warm, creative human variation
                max_tokens=350,
                top_p=0.9,
            )

            raw_reply = chat_completion.choices[0].message.content
            cleaned_reply = clean_bot_cliches(raw_reply)

            # Save assistant reply to memory DB
            save_message(session_id, "assistant", cleaned_reply)

            return {
                "response": cleaned_reply,
                "source": "groq",
                "model": selected_model
            }

        except Exception as e:
            print(f"Groq API call warning (using fallback): {e}")

    # 4. Fallback execution if Groq API key is missing or encounters rate limit
    mood = detect_mood_category(user_message)
    fallback_pool = FALLBACK_HUMAN_RESPONSES.get(mood, FALLBACK_HUMAN_RESPONSES["general"])
    reply = random.choice(fallback_pool)

    # Custom context tweak for fallback
    if "naam" in user_message.lower() or "name" in user_message.lower():
        reply = "Mera naam Saathi hai 😊 tera sachha dost! Tu batayega tera naam kya hai?"

    # Save fallback response to DB
    save_message(session_id, "assistant", reply)

    return {
        "response": reply,
        "source": "fallback",
        "model": "Saathi Human Engine"
    }
