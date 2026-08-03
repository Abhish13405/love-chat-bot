"""
AI Service Integration Engine (Groq + OpenAI API Support).
Includes anti-repetition frequency penalties, history deduplication, and ultra-realistic human response generation.
"""

import os
import random
from dotenv import load_dotenv
from persona_dataset import (
    COMPANION_PERSONAS,
    get_companion_prompt,
    get_smart_fallback_reply,
    clean_bot_cliches
)
from memory_db import get_recent_history, get_all_memories, save_message, set_memory_fact
from nlp_engine import analyze_user_sentiment, extract_user_entities

load_dotenv()

# Try loading Groq SDK
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Try loading OpenAI SDK
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def get_groq_client(custom_api_key=None):
    api_key = custom_api_key or os.getenv("GROQ_API_KEY")
    if GROQ_AVAILABLE and api_key and api_key.strip():
        try:
            return Groq(api_key=api_key.strip(), timeout=10.0)
        except Exception as e:
            print(f"Groq Init Notice: {e}")
            return None
    return None


def get_openai_client(custom_api_key=None):
    api_key = custom_api_key or os.getenv("OPENAI_API_KEY")
    if OPENAI_AVAILABLE and api_key and api_key.strip():
        try:
            return OpenAI(api_key=api_key.strip(), timeout=10.0)
        except Exception as e:
            print(f"OpenAI Init Notice: {e}")
            return None
    return None


def filter_dedup_history(history):
    """Filters out consecutive duplicate assistant messages to prevent LLM repetition loops."""
    clean_hist = []
    last_assistant_msg = ""
    for msg in history:
        if msg["role"] == "assistant":
            # Skip if exact duplicate of last assistant message
            if msg["content"].strip().lower() == last_assistant_msg.lower():
                continue
            last_assistant_msg = msg["content"].strip()
        clean_hist.append(msg)
    return clean_hist


def generate_companion_response(user_id: int, companion_id: str, user_message: str, custom_api_key: str = None) -> dict:
    companion_id = companion_id if companion_id in COMPANION_PERSONAS else "ananya"
    companion_info = COMPANION_PERSONAS[companion_id]

    # 1. NLP Entity Extraction (NER)
    try:
        extracted_fact = extract_user_entities(user_message)
        if extracted_fact and user_id:
            fact_key, fact_val = extracted_fact
            set_memory_fact(user_id, fact_key, fact_val)
    except Exception as e:
        print(f"NER extraction notice: {e}")

    # 2. NLP Sentiment Analysis
    try:
        emotions = analyze_user_sentiment(user_message)
        dominant_emotion = max(emotions, key=emotions.get) if any(emotions.values()) else "neutral"
    except Exception:
        dominant_emotion = "neutral"

    # Save user message
    try:
        save_message(user_id, companion_id, "user", user_message)
    except Exception as e:
        print(f"Save message notice: {e}")

    # 3. Get recent history & memories
    try:
        history = get_recent_history(user_id, companion_id, limit=14)
        history = filter_dedup_history(history)
        memories = get_all_memories(user_id) if user_id else {}
    except Exception:
        history = []
        memories = {}

    memory_snippet = ""
    if memories:
        items = [f"{k}: {v}" for k, v in memories.items()]
        memory_snippet = f"\n[User Facts Remembered: {', '.join(items)}]"

    nlp_snippet = f"\n[NLP Emotion Context: User dominant emotion is '{dominant_emotion}']"

    system_prompt = get_companion_prompt(companion_id) + memory_snippet + nlp_snippet

    # 4. Check for OpenAI Client first if key provided
    openai_client = get_openai_client(custom_api_key)
    if openai_client:
        try:
            messages = [{"role": "system", "content": system_prompt}]
            for msg in history:
                role = "assistant" if msg["role"] == "assistant" else "user"
                messages.append({"role": role, "content": msg["content"]})

            chat_completion = openai_client.chat.completions.create(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.8,
                max_tokens=100,
                presence_penalty=0.7,   # Strongly encourages introducing new topics
                frequency_penalty=0.7,  # Strongly prevents repeating words/phrases
            )

            raw_reply = chat_completion.choices[0].message.content
            cleaned_reply = clean_bot_cliches(raw_reply)

            try:
                save_message(user_id, companion_id, "assistant", cleaned_reply)
            except Exception:
                pass

            return {
                "response": cleaned_reply,
                "source": "openai",
                "model": "gpt-4o-mini",
                "emotion": dominant_emotion
            }
        except Exception as e:
            print(f"OpenAI API call notice: {e}")

    # 5. Check for Groq Client
    groq_client = get_groq_client(custom_api_key)
    selected_model = "llama-3.3-70b-versatile"

    if groq_client:
        try:
            messages = [{"role": "system", "content": system_prompt}]
            for msg in history:
                role = "assistant" if msg["role"] == "assistant" else "user"
                messages.append({"role": role, "content": msg["content"]})

            chat_completion = groq_client.chat.completions.create(
                messages=messages,
                model=selected_model,
                temperature=0.85,
                max_tokens=100,
                presence_penalty=0.7,   # Strongly encourages new topic creation
                frequency_penalty=0.7,  # Strictly penalizes word/phrase repetition!
                top_p=0.9,
            )

            raw_reply = chat_completion.choices[0].message.content
            cleaned_reply = clean_bot_cliches(raw_reply)

            try:
                save_message(user_id, companion_id, "assistant", cleaned_reply)
            except Exception:
                pass

            return {
                "response": cleaned_reply,
                "source": "groq",
                "model": selected_model,
                "emotion": dominant_emotion
            }

        except Exception as e:
            print(f"Groq API call notice: {e}")

    # 6. Smart Context Fallback
    gender = companion_info["gender"]
    reply = get_smart_fallback_reply(user_message, gender)

    try:
        save_message(user_id, companion_id, "assistant", reply)
    except Exception:
        pass

    return {
        "response": reply,
        "source": "fallback",
        "model": f"{companion_info['name']} Smart Engine",
        "emotion": dominant_emotion
    }
