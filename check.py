from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "my-secret-key-123")
CORS(app)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@app.route("/")
def index():
    session["history"] = []
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    if "history" not in session:
        session["history"] = []

    session["history"].append({
        "role": "user",
        "content": user_message
    })

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=session["history"],
        max_tokens=1024
    )

    reply = response.choices[0].message.content

    session["history"].append({
        "role": "assistant",
        "content": reply
    })

    session.modified = True
    return jsonify({"reply": reply})

@app.route("/clear", methods=["POST"])
def clear():
    session["history"] = []
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
