from flask import Flask, request, jsonify
from groq import Groq
from flask_cors import CORS
import os
import time
def safe_ai_call(messages, retries=2):
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
app = Flask(__name__)
CORS(app, origins=[
    "https://chatflow-ai-1.onrender.com",
    "https://chatflow.com",
    "https://backend-1-liqz.onrender.com"
])
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
        # DEFAULT MODE
        system = "Reply in 1 short natural sentence like in a phone call."

        if mode == "summary":
            system = "Summarize in 2 short sentences."

        elif mode == "ai_writer":
            system = (
                "You are a creative assistant. "
                "Rewrite the user's message in exactly 4 different ways. "
                "Format your response EXACTLY like this:\n"
                "1. [variation one]\n"
                "2. [variation two]\n"
                "3. [variation three]\n"
                "4. [variation four]\n"
                "Do NOT add any intro, explanation, or extra text. "
                "Only output the 4 numbered lines. Nothing else."
            )

        elif mode == "greeting":
            system = (
                "Transform the message into different greeting styles. "
                "Give 3-5 variations like casual, formal, friendly, slang."
            )

        # CUSTOM AI MODE
        if instructions and instructions.strip():
            system = f"""You are replying to chat messages like a real human (not an assistant).
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

        max_tokens = 400 if mode == "ai_writer" else 150

        completion = safe_ai_call([
    {"role": "system", "content": system},
    {"role": "user", "content": text}
])

        reply = completion.choices[0].message.content.strip()
        return jsonify({"reply": reply or "..."})

    except Exception as e:
        print("AI ERROR:", e)
        if "rate" in str(e).lower() or "limit" in str(e).lower():
            return jsonify({
                "message": "⚠️ AI request limit reached. Try again in 1 minute."
            }), 429
        return jsonify({
            "message": "AI error"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
