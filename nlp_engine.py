"""
Natural Language Processing (NLP) Engine for Saathi AI Companion.
Handles Sentiment Analysis, Emotion Scoring, Hinglish Token Normalization, 
and Automatic Entity & Fact Extraction (NER) for long-term memory.
"""

import re
from typing import Dict, Tuple, Optional


def normalize_hinglish_text(text: str) -> str:
    """Normalizes Hinglish text for NLP processing."""
    if not text:
        return ""
    text = text.lower().strip()
    # Normalize excessive repeated letters (e.g., "yaaaar" -> "yaar")
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)
    return text


def analyze_user_sentiment(text: str) -> Dict[str, float]:
    """
    NLP Sentiment & Emotion Analyzer.
    Returns sentiment scores: {"loneliness": float, "stress": float, "happiness": float, "sadness": float}
    """
    clean_text = normalize_hinglish_text(text)
    
    scores = {
        "loneliness": 0.0,
        "stress": 0.0,
        "sadness": 0.0,
        "happiness": 0.0
    }

    # Keyword patterns for Hinglish emotion detection
    lonely_keywords = ["akela", "akele", "lonely", "alone", "koi nhi", "koi nahi", "miss", "sath nhi", "saath nahi"]
    stress_keywords = ["stress", "tension", "worried", "office", "work", "exam", "load", "thak", "tired", "headache"]
    sad_keywords = ["udaas", "sad", "rula", "ro", "kharaab", "bekaar", "hurt", "pain", "bura", "low"]
    happy_keywords = ["khush", "happy", "mast", "great", "party", "mza", "maza", "awesome", "lol", "haha"]

    for kw in lonely_keywords:
        if kw in clean_text:
            scores["loneliness"] += 0.4

    for kw in stress_keywords:
        if kw in clean_text:
            scores["stress"] += 0.4

    for kw in sad_keywords:
        if kw in clean_text:
            scores["sadness"] += 0.4

    for kw in happy_keywords:
        if kw in clean_text:
            scores["happiness"] += 0.4

    # Cap scores at 1.0
    for k in scores:
        scores[k] = min(1.0, scores[k])

    return scores


def extract_user_entities(text: str) -> Optional[Tuple[str, str]]:
    """
    NLP Named Entity & Fact Extractor (NER).
    Extracts facts like Name, Location, Favorite Food, Hobbies from natural conversation.
    Returns tuple: (fact_key, fact_value) or None
    """
    clean = text.strip()

    # 1. Extract Name ("Mera naam Abhi hai", "My name is Abhi", "I am Abhi")
    name_match = re.search(r'(?:mera\s+naam|my\s+name\s+is|main|i\s+am)\s+([A-Za-z]+)', clean, re.IGNORECASE)
    if name_match:
        extracted = name_match.group(1).capitalize()
        if extracted.lower() not in ["hu", "hai", "is", "a", "the", "ek"]:
            return ("Name", extracted)

    # 2. Extract Favorite Food ("Mujhe biryani pasand hai", "I love pizza")
    food_match = re.search(r'(?:mujhe|i\s+love|i\s+like)\s+([A-Za-z]+)\s+(?:pasand|khana)', clean, re.IGNORECASE)
    if food_match:
        return ("Favorite Food", food_match.group(1).capitalize())

    # 3. Extract City/Location ("Main Delhi me rehta hu", "I live in Mumbai")
    city_match = re.search(r'(?:main|i\s+live\s+in)\s+([A-Za-z]+)\s+(?:me|me\s+rehta|me\s+rehti|city)', clean, re.IGNORECASE)
    if city_match:
        extracted = city_match.group(1).capitalize()
        if extracted.lower() not in ["ghar", "room", "office"]:
            return ("City", extracted)

    return None
