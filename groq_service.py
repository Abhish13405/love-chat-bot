"""
AI Service Router for Saathi Companion.
Routes chat messages through Groq LLM API with smart fallback.
"""

import os
from dotenv import load_dotenv
from persona_dataset import COMPANION_PERSONAS, clean_bot_cliches, get_smart_fallback_reply
from memory_db import get_recent_history, save_message, set_memory_fact
from nlp_engine import analyze_user_sentiment, extract_user_entities

load_dotenv()

# Optional Cloud SDK imports
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

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
        except Exception:
            return None
    return None


def get_openai_client(custom_api_key=None):
    api_key = custom_api_key or os.getenv("OPENAI_API_KEY")
    if OPENAI_AVAILABLE and api_key and api_key.strip():
        try:
            return OpenAI(api_key=api_key.strip(), timeout=10.0)
        except Exception:
            return None
    return None


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
        print(f"NER notice: {e}")

    # 2. NLP Sentiment Analysis
    try:
        emotions = analyze_user_sentiment(user_message)
        dominant_emotion = max(emotions, key=emotions.get) if any(emotions.values()) else "neutral"
    except Exception:
        dominant_emotion = "neutral"

    # 3. Save User Message
    try:
        save_message(user_id, companion_id, "user", user_message)
    except Exception as e:
        print(f"Save message notice: {e}")


    # 4. Optional OpenAI API Execution
    openai_client = get_openai_client(custom_api_key)
    if openai_client:
        try:
            history = get_recent_history(user_id, companion_id, limit=10)
            messages = [{"role": "system", "content": companion_info["prompt"]}]
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})

            completion = openai_client.chat.completions.create(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.8,
                max_tokens=100,
                presence_penalty=0.7,
                frequency_penalty=0.7
            )
            reply = clean_bot_cliches(completion.choices[0].message.content)
            save_message(user_id, companion_id, "assistant", reply)
            return {"response": reply, "source": "openai", "model": "gpt-4o-mini", "emotion": dominant_emotion}
        except Exception as e:
            print(f"OpenAI notice: {e}")

    # 5. Optional Groq API Execution
    groq_client = get_groq_client(custom_api_key)
    if groq_client:
        try:
            history = get_recent_history(user_id, companion_id, limit=10)
            messages = [{"role": "system", "content": companion_info["prompt"]}]
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})

            completion = groq_client.chat.completions.create(
                messages=messages,
                model="llama-3.3-70b-versatile",
                temperature=0.8,
                max_tokens=100,
                presence_penalty=0.7,
                frequency_penalty=0.7
            )
            reply = clean_bot_cliches(completion.choices[0].message.content)
            save_message(user_id, companion_id, "assistant", reply)
            return {"response": reply, "source": "groq", "model": "llama-3.3-70b", "emotion": dominant_emotion}
        except Exception as e:
            print(f"Groq notice: {e}")

    # 6. Smart Fallback (Persona-aware keyword matching - no robotic responses)
    reply = get_smart_fallback_reply(user_message, companion_info["gender"])

    try:
        save_message(user_id, companion_id, "assistant", reply)
    except Exception:
        pass

    return {
        "response": reply,
        "source": "smart_fallback",
        "model": f"{companion_info['name']} Offline Mode",
        "emotion": dominant_emotion
    }
