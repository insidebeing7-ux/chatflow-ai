from flask import Flask, request, jsonify
from groq import Groq
from flask_cors import CORS
import os

app = Flask(__name__)

# allow your Netlify frontend
CORS(app, origins=[
    "https://cheerful-caramel-d22102.netlify.app"
])

# Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


@app.route("/ai", methods=["POST"])
def ai_reply():
    data = request.json or {}

    text = (data.get("text", "") or "")[-2000:]
    mode = data.get("mode", "chat")
    instructions = data.get("instructions", "")

    if not text.strip():
        return jsonify({"reply": "..."})

    try:
        # ================= BASE SYSTEM =================
        system = "Reply in 1 short natural sentence like in a phone call."

        # ================= MODES =================
        if mode == "summary":
            system = "Summarize in 2 short sentences."

        elif mode == "ai_writer":
            system = (
                "You are a creative assistant. "
                "Rewrite the user's message in 3–6 short variations, each on a new line."
            )

        elif mode == "greeting":
            system = (
                "Give 3–5 greeting styles: casual, formal, friendly, slang."
            )

        # ================= CUSTOM MODE OVERRIDE =================
        if instructions and instructions.strip():
            system = f"""
You are replying like a real human in chat.

USER-DEFINED BEHAVIOR:
{instructions}

RULES:
- Follow instructions strictly
- Keep replies short
- Never mention that you are an AI
"""

        # ================= GROQ CALL =================
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text}
            ],
            temperature=0.8,
            max_completion_tokens=80
        )

        reply = completion.choices[0].message.content.strip()
        return jsonify({"reply": reply or "..."})

    except Exception as e:
        print("🔥 GROQ ERROR:", e)

        # optional rate-limit hint
        if "rate" in str(e).lower() or "limit" in str(e).lower():
            return jsonify({
                "message": "⚠️ AI request limit reached. Try again in 1 minute."
            }), 429

        return jsonify({
            "message": "AI error"
        }), 500


# ================= HEALTH CHECK =================
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "AI server running"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
