from flask import Flask, request, jsonify
from groq import Groq
from flask_cors import CORS
import os
import time

app = Flask(__name__)
CORS(app, origins=[
    "https://chatflow-ai-1.onrender.com",
    "https://chatflow.com",
    "https://backend-1-liqz.onrender.com"
])

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def safe_ai_call(messages, max_tokens, retries=2):
    for i in range(retries + 1):
        try:
            return client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.8,
                max_completion_tokens=max_tokens,
                timeout=20
            )
        except Exception as e:
            if i == retries:
                raise e
            time.sleep(0.5)


@app.route("/ai", methods=["POST"])
def ai_reply():
    data = request.json
    text = data.get("text", "")[-2000:]
    mode = data.get("mode", "chat")
    instructions = data.get("instructions", "")

    if not text.strip():
        return jsonify({"reply": "..."})

    try:
        # DEFAULT SYSTEM PROMPT
        system = "Reply in 1 short natural sentence like in a phone call."

        if mode == "summary":
            system = "Summarize in 2 short sentences."

        elif mode == "ai_writer":
            system = (
                "You are a creative assistant. "
                "Rewrite the user's message in exactly 4 different ways. "
                "Format your response EXACTLY like this:\n"
                "1. ...\n2. ...\n3. ...\n4. ...\n"
                "Do NOT add extra text."
            )

        elif mode == "greeting":
            system = (
                "Transform the message into different greeting styles. "
                "Give 3-5 variations like casual, formal, friendly, slang."
            )

        # CUSTOM AI MODE (FIXED INDENTATION)
        if instructions and instructions.strip():
            system = f"""
You are replying to chat messages like a real human.

USER-DEFINED BEHAVIOR:
{instructions}

RULES:
- Follow instructions strictly
- Keep replies short (1 sentence)
- Never sound like an AI assistant
"""

        # token control
        max_tokens = 400 if mode == "ai_writer" else 150

        completion = safe_ai_call(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": text}
            ],
            max_tokens=max_tokens
        )

        reply = completion.choices[0].message.content.strip()
        return jsonify({"reply": reply or "..."})

    except Exception as e:
        print("AI ERROR:", e)

        if "rate" in str(e).lower() or "limit" in str(e).lower():
            return jsonify({"message": "⚠️ AI request limit reached."}), 429

        return jsonify({"message": "AI error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
