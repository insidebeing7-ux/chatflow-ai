from flask import Flask, request, jsonify
from groq import Groq
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app, origins=["https://cheerful-caramel-d22102.netlify.app"])

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@app.route("/ai", methods=["POST"])
def ai_reply():
    data = request.json

    text = data.get("text", "")[-2000:]
    mode = data.get("mode", "chat")
    instructions = data.get("instructions", "")

    if not text.strip():
        return jsonify({"reply": "..."})

    try:

        # ✅ DEFAULT MODE (normal chat)
        system = "Reply in 1 short natural sentence like in a phone call."

        # 🔥 MODE 1: SUMMARY
        if mode == "summary":
            system = "Summarize in 2 short sentences."

        # 🔥 MODE 2: AI WRITER (YOUR send_ai.js FEATURE)
        elif mode == "ai_writer":
            system = (
                "You are a creative assistant. "
                "Rewrite the user's message in multiple different ways. "
                "Give 3 to 6 short variations, each on a new line. "
                "Do NOT answer normally, only rephrase creatively."
            )

        # 🔥 MODE 3: GREETING STYLE (optional extra)
       system = "Reply in 1 short natural sentence like in a phone call."

if mode == "summary":
    system = "Summarize in 2 short sentences."

elif mode == "ai_writer":
    system = "Rewrite in 3–6 short variations, each on a new line."

elif mode == "greeting":
    system = "Give 3–5 greeting styles (casual, formal, slang)."

# 👇 CUSTOM MODE (MUST BE LAST)
if instructions and instructions.strip():
    system = f"""
You are replying like a real human.

USER-DEFINED BEHAVIOR:
{instructions}

RULES:
- Follow strictly
- Keep replies short
- Never act like assistant
"""
    
@app.route("/ai", methods=["POST"])
def ai_reply():
        try:
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
    return jsonify({"reply": "AI error"}), 500

    except Exception as e:
     print("AI ERROR:", e)

    # 🔥 detect rate limit
     if "rate" in str(e).lower() or "limit" in str(e).lower():
        return jsonify({
            "message": "⚠️ AI request limit reached. Try again in 1 minute."
        }), 429

    return jsonify({
        "message": "AI error"
    }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
