"""
Flask Application Entry Point for AI Companion (Saathi).
"""

import os
import uuid
from flask import Flask, render_template, request, jsonify, session
from groq_service import generate_companion_response
from memory_db import get_recent_history, clear_history, get_all_memories, set_memory_fact

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "saathi_lonely_companion_secret_key_9988")


@app.before_request
def ensure_session():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    custom_api_key = data.get("api_key", "").strip()

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    session_id = session.get("session_id", str(uuid.uuid4()))
    
    # Generate reply
    result = generate_companion_response(session_id, user_message, custom_api_key)
    
    return jsonify({
        "status": "success",
        "response": result["response"],
        "source": result["source"],
        "model": result["model"],
        "session_id": session_id
    })


@app.route("/api/history", methods=["GET"])
def history():
    session_id = session.get("session_id", "")
    chats = get_recent_history(session_id, limit=30)
    return jsonify({"status": "success", "history": chats})


@app.route("/api/clear", methods=["POST"])
def clear():
    session_id = session.get("session_id", "")
    clear_history(session_id)
    return jsonify({"status": "success", "message": "Chat history cleared."})


@app.route("/api/memory", methods=["GET", "POST"])
def memory():
    if request.method == "POST":
        data = request.get_json() or {}
        key = data.get("key", "").strip()
        value = data.get("value", "").strip()
        if key and value:
            set_memory_fact(key, value)
            return jsonify({"status": "success", "message": f"Remembered: {key}"})
        return jsonify({"error": "Invalid memory payload"}), 400
    else:
        memories = get_all_memories()
        return jsonify({"status": "success", "memories": memories})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n==========================================")
    print(f"  Saathi AI Companion App running on http://127.0.0.1:{port}")
    print(f"==========================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)
