from flask import Flask, request, jsonify
from groq import Groq
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app, origins=["https://chatflow.com"])

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
        elif mode == "greeting":
            system = (
                "Transform the message into different greeting styles. "
                "Give 3–5 variations like casual, formal, friendly, slang."
            )
          # ================= CUSTOM AI MODE (FIXED PLACE) =================
        if instructions and instructions.strip():
            system = f"""
            You are replying to chat messages like a real human (not an assistant).


USER-DEFINED BEHAVIOR:
{instructions}

RULES:
- Follow the USER-DEFINED BEHAVIOR strictly
- Adapt to the message tone (polite, casual, etc.)
- Keep replies short (1 sentence)
- Never act like an AI assistant
- Never say things like "How can I help you?"
- Never be generic or robotic
- If instructions say "be short", you MUST be short.
- If instructions say "only questions", you ONLY ask questions.
- If instructions say "no replies", output nothing.
- You are NOT allowed to ignore instructions or add extra behavior.
"""
    

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text}
            ],
            temperature=0.8,
            max_completion_tokens=150
        )

        reply = completion.choices[0].message.content.strip()
        return jsonify({"reply": reply or "..."})

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
