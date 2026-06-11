from flask import Flask, request, jsonify
from groq import Groq
from flask_cors import CORS
import os
import time
import json
import threading
import requests

app = Flask(__name__)
CORS(app, origins=[
    "https://chatflow-ai-1.onrender.com",
    "https://chatflow.com",
    "https://backend-1-liqz.onrender.com",
    "https://backend-1-liqz.onrender.com"
])

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROUNDING_RULES = """
STRICT RULES — NEVER BREAK THESE:
- You do NOT know the user's real name, age, location, or any personal detail unless they just told you in this exact message.
- Never invent names, facts, or context. If you don't know something, say so briefly.
- Never greet the user by a name you were not explicitly given.
- Do not make assumptions about who the user is or what they want beyond what they wrote.
- Stay strictly within the scope of the user's message. Do not add unrelated information.
- If the message is a greeting like "hello", reply with a simple greeting only — no names, no invented context.
"""
def safe_ai_call(messages, max_tokens, retries=2, use_json=False):
    for i in range(retries + 1):
        try:
            kwargs = dict(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.4,
                max_completion_tokens=max_tokens,
                timeout=30
            )
            if use_json:
                kwargs["response_format"] = {"type": "json_object"}
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            if i == retries:
                raise e
            time.sleep(0.5)

@app.route("/ai", methods=["POST"])
def ai():
    data = request.get_json()
    text = data.get("text", "")
    mode = data.get("mode", "default")
    instructions = data.get("instructions", "")

    try:
        system = "Reply in 1 short natural sentence like in a phone call."

        if mode == "summary":
            system = "Summarize in 2 short sentences."
        elif mode == "ai_writer":
            system = (
                "You are a creative message rewriter for a chat app. "
                "The user gives you a message they want to SEND. "
                "Your job is to rewrite it in 4 different creative styles (casual, funny, formal, expressive). "
                "Do NOT answer the message. Do NOT reply to it. ONLY rewrite it in different ways. "
                "Example: if the user gives you 'how are you', return 4 ways to say 'how are you' — not answers to it. "
                "You MUST respond with ONLY this exact JSON format, nothing else:\n"
                "{\"results\": [\"version 1\", \"version 2\", \"version 3\", \"version 4\"]}\n"
                "Do NOT add any explanation, greeting, or text outside the JSON. "
                "Do NOT use markdown. Do NOT number the items. "
                "Each result must be a natural chat message that means the same thing as the input."
            )
        elif mode == "greeting":
            system = (
                "Transform the message into different greeting styles. "
                "Give 3-5 variations like casual, formal, friendly, slang."
            )

        if instructions and instructions.strip() and mode != "ai_writer":
            system = f"""You are a chat assistant replying to messages on behalf of a user.

USER-DEFINED BEHAVIOR:
{instructions}

{GROUNDING_RULES}

RESPONSE RULES:
- Reply in 1 short, natural sentence as if texting a friend.
- Follow the user-defined behavior above strictly.
- Never sound like an AI assistant or customer support agent.
- Never greet by name unless the name was given in this exact message.
- Do not add sign-offs, emojis, or extra commentary unless the behavior instructs it.
"""
        else:
            system = f"""You are a chat assistant replying to messages on behalf of a user.

{GROUNDING_RULES}

RESPONSE RULES:
- Reply in 1 short, natural sentence as if texting a friend.
- Match the tone of the incoming message (casual stays casual, serious stays serious).
- Never sound like an AI assistant.
- Never greet by name unless a name was given in this exact message.
- If the message is just a greeting like "hi" or "hello", reply with only a simple greeting — nothing else.
"""

        max_tokens = 400 if mode == "ai_writer" else 150

        completion = safe_ai_call(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": text}
            ],
            max_tokens=max_tokens,
            use_json=(mode == "ai_writer")
        )

        reply = completion.choices[0].message.content.strip()

        if mode == "ai_writer":
            try:
                parsed = json.loads(reply)
                if not isinstance(parsed.get("results"), list) or len(parsed["results"]) < 2:
                    raise ValueError("bad results")
            except Exception:
                clean = reply.replace('"', "'").strip()
                fallback = {
                    "results": [
                        clean,
                        clean + "! 😊",
                        "Hey, " + clean + "?",
                        clean + " — just checking in!"
                    ]
                }
                return jsonify({"reply": json.dumps(fallback)})

        return jsonify({"reply": reply or "..."})

    except Exception as e:
        print("AI ERROR:", e)
        if "rate" in str(e).lower() or "limit" in str(e).lower():
            return jsonify({"message": "⚠️ AI request limit reached."}), 429
        return jsonify({"message": "AI error"}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

def self_ping():
    while True:
        time.sleep(13 * 60)
        try:
            url = os.getenv("SELF_URL", "https://chatflow-ai-1.onrender.com")
            requests.post(url + "/ai", json={
                "text": "hi",
                "mode": "chat",
                "instructions": ""
            }, timeout=10)
            print("✅ Self-ping sent")
        except Exception as e:
            print("⚠️ Self-ping failed:", e)

threading.Thread(target=self_ping, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
