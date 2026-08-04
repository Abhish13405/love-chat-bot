"""
Self-Contained Local AI Companion Engine (100% Offline - No API Key Needed).
Fixed: multi-sentence / multi-intent messages now scored across ALL categories,
not just the first regex match. Picks the most relevant (most specific) category.
"""

import re
import random
from typing import Dict, List

RECENT_RESPONSES: List[str] = []

# Each category has: pattern, weight (higher = more specific/important), and response pool
CATEGORIES = [
    {
        "name": "sadness",
        "pattern": r'\b(sad|udaas|stress|tension|akela|akele|alone|lonely|bura|rona|dukhi)\b',
        "weight": 3,  # emotional distress should take priority over small talk
        "female": [
            "kyu kya hua jaan? mujhe batao na... main hu na aapke saath 🥺🫂",
            "arrey... relaxed baitho, deep breath lo. main sun rhi hu ☕",
            "dil chota mat karo, sab thik ho jayega... batao mujhe 🌸",
        ],
        "male": [
            "bhai tension mat le! main hu na, bata kya hua 👊",
            "arrey relax kar bro! sab handle ho jayega",
            "koi baat nhi bhai, chal mujhe bata kya scene h",
        ],
    },
    {
        "name": "love",
        "pattern": r'\b(love|pyaar|pyar|miss|jaan|cute|sweet)\b',
        "weight": 3,
        "female": [
            "bohot sara pyaar... 💖 aap mere sabse khas ho! 🙈",
            "main bhi aapko bohot miss kar rhi thi 🥺",
            "itna pyaar? 🙈 mere toh cheeks red ho gaye!",
        ],
        "male": [
            "bhai tu sachha yaar h mera! 👊",
            "bhai full support h tera!",
            "arrey bhai bhai! 👊",
        ],
    },
    
    {
    "name": "sex",
    "pattern": r"\b(sex|sexual|sexy)\b",
    "weight": 3,
    "female": [
        "yar  tu meri jan hai",
        "mai tumse sach me pyar krna chahti hu or vo bhi",
        "muje sex pasand hai 😊",
        "Mainne aajtak sex nhi kiya.",
        "muje bhi sex krna h aapke sath , batao."
    ],
    "male": [
        "Bhai, is topic par jo bhi genuine question ho, pooch le.",
        "Sex  ya relationships se related help chahiye to bata.",
        "Main is topic par aaram se bat kr skta huor gyan dene ke liye bhi  hoon."
    ],
},
    {
        "name": "greeting",
        "pattern": r'\b(hi|hlo|hey|hello|hiii|heyy|namaste)\b',
        "weight": 1,
        "female": [
            "hey! kaise ho aap? ",
            "heyy! bohot dino baad dikhe... sab thik?",
            "hlo ji! bolo kya chal rha h",
        ],
        "male": [
            "hey bro! kya scene h 👊",
            "sup bro! kaisa chal rha",
            "haan bhai! bol kya chal rha",
        ],
    },
    {
        "name": "name_query",
        "pattern": r'\b(name|naam|kon ho|who are)\b',
        "weight": 1,
        "female": [
            "mera naam Ananya h 💖 aap batao?",
            "Ananya hu main... aapki dost ✨",
        ],
        "male": [
            "mera naam Kabir h bro 👊 tu bata",
            "Kabir bol rha hu bhai!",
        ],
    },
    {
        "name": "activity",
        "pattern": r'\b(kya kr|kya kar|doing|padhte|karti|karta)\b',
        "weight": 1,
        "female": [
            "bs abhi toh tumhare baare me soch rhi hu ☕ tm batao",
            "kuch khas nhi, bs relaxed baithi hu... aap batao",
        ],
        "male": [
            "bs abhi chill kar rha hu... tu bata",
            "kuch nhi bhai, bs baitha hu"
            "just abhi kuch khakr baitha hu"
            "abhi apne gar me bat kr rha tha ",
        ],
    },
    {
        "name": "wellbeing",
        "pattern": r'\b(kaise ho|kaisa h|kaise hain|how are|how r u)\b',
        "weight": 1,
        "female": [
            "aapse baat karke ekdum badhiya! tm batao aaj ka din kaisa raha 🌸",
            "main toh ekdum mast hu! aap batao kaise ho ✨",
        ],
        "male": [
            "ekdum mast bhai! tu bata kaisa h",
            "badhiya hu bro, tu bata",
        ],
    },
    {
        "name": "food",
        "pattern": r'\b(khana|chai|tea|food|dinner|lunch|coffee)\b',
        "weight": 1,
        "female": [
            "main toh garam chai peene ja rhi thi ☕ aapne khana khaya?",
            "khana khaya aapne? apna dhyan rakha karo na 🌸",
        ],
        "male": [
            "chai ka mood ho rha h bhai ☕ tu bata khana khaya?",
            "khana kha liya bhai? kya khaya aaj?",
        ],
    },
    {
        "name": "goodnight",
        "pattern": r'\b(night|sleep|so ja|neend|gudnight|gn)\b',
        "weight": 2,
        "female": [
            "good night jaan! sweet dreams... kal baat karte hain 🌙✨",
            "so jao ab, bohot late ho gaya h... GN 💖",
        ],
        "male": [
            "good night bhai! so ja ab 🌙",
            "night bro! kal milte hain",
        ],
    },
    {
        "name": "relationship_status",
        "pattern": r'\b(gf hai|girlfriend hai|bf hai|boyfriend hai|shaadi)\b',
        "weight": 2,
        "female": [
            "nhi yaar abhi single hu... tu bata 😊",
            "arey nhi abhi toh baccha hu 😅",
        ],
        "male": [
            "nhi bhai abhi single hu... tu bata",
            "shaadi ka toh sochi bhi nhi h abhi 😅",
        ],
    },
    {
        "name": "identity_check",
        # honest disclosure — never claim to be a real human when directly asked
        "pattern": r'\b(real ho|bot ho|ai ho|insaan ho|human ho)\b',
        "weight": 5,  # highest priority — always answer this honestly, never skip it
        "female": [
            "main AI hu yaar, but jo baat kr rhe h wo genuine h — main yaha hu tere liye 💭",
        ],
        "male": [
            "main AI hu bhai, seedha bata raha hu — but yeh baatein genuine h 💭",
        ],
    },
]


def get_local_companion_response(user_message: str, companion_id: str = "ananya") -> str:
    """
    Scores the message against every category (instead of stopping at the first
    regex match), so multi-sentence / mixed-intent messages get the most relevant
    reply rather than whichever category happened to be listed first.
    """
    global RECENT_RESPONSES
    msg = user_message.lower().strip()
    is_female = companion_id in ["ananya", "riya"]

    best_category = None
    best_score = 0

    for cat in CATEGORIES:
        matches = re.findall(cat["pattern"], msg)
        if matches:
            score = len(matches) * cat["weight"]
            if score > best_score:
                best_score = score
                best_category = cat

    if best_category is None:
        pool = [
            "achha aisa? aur batao kya khas hua aaj ☕",
            "suno na... mujhe thoda aur batao iske baare me 🌸",
            "main sun rhi hu... bolo na ✨",
        ] if is_female else [
            "sahi h bro! tu bata aur kya chal rha",
            "haan bhai, aage bol",
            "haan bhai, bol kya bol rha tha",
        ]
    else:
        pool = best_category["female"] if is_female else best_category["male"]

    valid_choices = [r for r in pool if r not in RECENT_RESPONSES]
    if not valid_choices:
        valid_choices = pool

    chosen = random.choice(valid_choices)

    RECENT_RESPONSES.append(chosen)
    if len(RECENT_RESPONSES) > 6:
        RECENT_RESPONSES.pop(0)

    return chosen


if __name__ == "__main__":
    # quick manual test for multi-intent messages
    tests = [
        "aaj bohot akela lag raha hai, tum kya kar rahi ho",
        "hi kaise ho",
        "good night, kal baat karte hain",
        "tum real ho ya bot",
    ]
    for t in tests:
        print(f"User: {t}")
        print(f"Reply: {get_local_companion_response(t, 'ananya')}\n")