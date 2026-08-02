"""
Flask Server Entry Point for Saathi AI Companion with Auth & Multi-Gender Personas.
"""

import os
from flask import Flask, render_template, request, jsonify, session
from groq_service import generate_companion_response
from persona_dataset import COMPANION_PERSONAS
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


# --- AUTH ROUTES ---

@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json() or {}
    username = data.get("username", "")
    password = data.get("password", "")
    display_name = data.get("display_name", "")

    result = register_user(username, password, display_name)
    if result["success"]:
        session["user_id"] = result["user"]["id"]
        session["username"] = result["user"]["username"]
        session["display_name"] = result["user"]["display_name"]
        return jsonify({"status": "success", "user": result["user"]})
    return jsonify({"status": "error", "error": result["error"]}), 400


@app.route("/api/login", methods=["POST"])
def login():
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
    # Return persona list without raw system prompts
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
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    companion_id = data.get("companion_id", "ananya").strip()
    custom_api_key = data.get("api_key", "").strip()

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    user_id = session.get("user_id")

    # Generate response
    result = generate_companion_response(user_id, companion_id, user_message, custom_api_key)

    return jsonify({
        "status": "success",
        "response": result["response"],
        "source": result["source"],
        "model": result["model"],
        "companion_id": companion_id
    })


@app.route("/api/history", methods=["GET"])
def history():
    user_id = session.get("user_id")
    companion_id = request.args.get("companion_id", "ananya").strip()
    chats = get_recent_history(user_id, companion_id, limit=30)
    return jsonify({"status": "success", "history": chats})


@app.route("/api/clear", methods=["POST"])
def clear():
    user_id = session.get("user_id")
    data = request.get_json() or {}
    companion_id = data.get("companion_id", "ananya").strip()
    clear_history(user_id, companion_id)
    return jsonify({"status": "success", "message": "History cleared."})


@app.route("/api/memory", methods=["GET", "POST"])
def memory():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "error": "Login required for personal memories"}), 401

    if request.method == "POST":
        data = request.get_json() or {}
        key = data.get("key", "").strip()
        value = data.get("value", "").strip()
        if key and value:
            set_memory_fact(user_id, key, value)
            return jsonify({"status": "success", "message": f"Remembered: {key}"})
        return jsonify({"error": "Invalid memory payload"}), 400
    else:
        memories = get_all_memories(user_id)
        return jsonify({"status": "success", "memories": memories})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n==========================================")
    print(f"  Saathi Multi-Gender AI Companion on http://127.0.0.1:{port}")
    print(f"==========================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)
