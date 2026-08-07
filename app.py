"""
Flask Server Entry Point for Saathi AI Companion with Auth & Multi-Gender Personas.
Includes error handling against connection reset and network glitches.
"""

import os
from flask import Flask, render_template, request, jsonify, session
from groq_service import generate_companion_response
from persona_dataset import COMPANION_PERSONAS, get_smart_fallback_reply
from memory_db import (
    register_user,
    authenticate_user,
    get_recent_history,
    clear_history,
    get_all_memories,
    set_memory_fact
)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "saathi_lonely_companion_secret_key_9988")
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.before_request
def ensure_session():
    if "session_id" not in session:
        session["session_id"] = "guest_session"


# --- AUTH ROUTES ---

@app.route("/api/signup", methods=["POST"])
def signup():
    try:
        data = request.get_json() or {}
        username = data.get("username", "")
        password = data.get("password", "")
        display_name = data.get("display_name", "")
        email = data.get("email", "")

        result = register_user(username, password, display_name, email)
        if result["success"]:
            session["user_id"] = result["user"]["id"]
            session["username"] = result["user"]["username"]
            session["display_name"] = result["user"]["display_name"]
            session["email"] = result["user"].get("email", "")
            return jsonify({"status": "success", "user": result["user"]})
        return jsonify({"status": "error", "error": result["error"]}), 400
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/login", methods=["POST"])
def login():
    try:
        data = request.get_json() or {}
        username = data.get("username", "")
        password = data.get("password", "")

        result = authenticate_user(username, password)
        if result["success"]:
            session["user_id"] = result["user"]["id"]
            session["username"] = result["user"]["username"]
            session["display_name"] = result["user"]["display_name"]
            return jsonify({"status": "success", "user": result["user"]})
        return jsonify({"status": "error", "error": result["error"]}), 401
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "success", "message": "Logged out"})


@app.route("/api/me", methods=["GET"])
def me():
    if "user_id" in session:
        return jsonify({
            "status": "authenticated",
            "user": {
                "id": session["user_id"],
                "username": session["username"],
                "display_name": session.get("display_name", session["username"])
            }
        })
    return jsonify({"status": "guest", "user": None})


# --- CHAT & PERSONA ROUTES ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/personas", methods=["GET"])
def personas():
    list_personas = []
    for pid, data in COMPANION_PERSONAS.items():
        list_personas.append({
            "id": data["id"],
            "name": data["name"],
            "gender": data["gender"],
            "role": data["role"],
            "avatar": data["avatar"],
            "description": data["description"],
            "badge": data["badge"]
        })
    return jsonify({"status": "success", "personas": list_personas})


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Authentication required. Please login or register."}), 401

        data = request.get_json() or {}
        user_message = data.get("message", "").strip()
        companion_id = data.get("companion_id", "ananya").strip()
        custom_api_key = data.get("api_key", "").strip()

        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400

        # Generate response safely
        result = generate_companion_response(user_id, companion_id, user_message, custom_api_key)

        return jsonify({
            "status": "success",
            "response": result["response"],
            "source": result["source"],
            "model": result["model"],
            "companion_id": companion_id
        })
    except Exception as e:
        print(f"Connection/Chat handler warning: {e}")
        cid = request.get_json().get("companion_id", "ananya") if request.get_json() else "ananya"
        msg = request.get_json().get("message", "") if request.get_json() else ""
        gender = COMPANION_PERSONAS.get(cid, {}).get("gender", "female")
        fallback_resp = get_smart_fallback_reply(msg, gender) if msg else "hnn main sun rhi hu... thoda network glitch tha, wapas bolo na! ☕"
        return jsonify({
            "status": "success",
            "response": fallback_resp,
            "source": "fallback",
            "model": "Saathi Dynamic Safety Engine",
            "companion_id": cid
        })


@app.route("/api/history", methods=["GET"])
def history():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"status": "success", "history": []})
        companion_id = request.args.get("companion_id", "ananya").strip()
        chats = get_recent_history(user_id, companion_id, limit=30)
        return jsonify({"status": "success", "history": chats})
    except Exception as e:
        return jsonify({"status": "success", "history": []})


@app.route("/api/clear", methods=["POST"])
def clear():
    try:
        user_id = session.get("user_id")
        data = request.get_json() or {}
        companion_id = data.get("companion_id", "ananya").strip()
        clear_history(user_id, companion_id)
        return jsonify({"status": "success", "message": "History cleared."})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/memory", methods=["GET", "POST"])
def memory():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "error": "Login required for personal memories"}), 401

    if request.method == "POST":
        try:
            data = request.get_json() or {}
            key = data.get("key", "").strip()
            value = data.get("value", "").strip()
            if key and value:
                set_memory_fact(user_id, key, value)
                return jsonify({"status": "success", "message": f"Remembered: {key}"})
            return jsonify({"error": "Invalid memory payload"}), 400
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500
    else:
        try:
            memories = get_all_memories(user_id)
            return jsonify({"status": "success", "memories": memories})
        except Exception as e:
            return jsonify({"status": "success", "memories": {}})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n==========================================")
    print(f"  Saathi Multi-Gender AI Companion on http://127.0.0.1:{port}")
    print(f"==========================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)
