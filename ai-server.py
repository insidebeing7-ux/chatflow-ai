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
    "https://testback-4sru.onrender.com"
])

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def safe_ai_call(messages, max_tokens, retries=2, use_json=False):
    for i in range(retries + 1):
        try:
            kwargs = dict(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.4,   # Lower = less hallucination
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

# ── Core anti-hallucination rules injected into every prompt ──────────────────
GROUNDING_RULES = """
STRICT RULES — NEVER BREAK THESE:
- You do NOT know the user's real name, age, location, or any personal detail unless they just told you in this exact message.
- Never invent names, facts, or context. If you don't know something, say so briefly.
- Never greet the user by a name you were not explicitly given.
- Do not make assumptions about who the user is or what they want beyond what they wrote.
- Stay strictly within the scope of the user's message. Do not add unrelated information.
- If the message is a greeting like "hello", reply with a simple greeting only — no names, no invented context.
"""

@app.route("/ai", methods=["POST"])
def ai():
    data = request.get_json()
    text = (data.get("text", "") or "").strip()
    mode = data.get("mode", "default")
    instructions = (data.get("instructions", "") or "").strip()

    if not text:
        return jsonify({"reply": "..."}), 200

    try:
        # ── MODE: ai_writer ───────────────────────────────────────────────────
        if mode == "ai_writer":
            system = (
                "You are a creative message rewriter for a chat app. "
                "The user gives you a message they want to SEND. "
                "Your job is to rewrite it in 4 different creative styles: casual, funny, formal, expressive. "
                "Do NOT answer the message. Do NOT reply to it. ONLY rewrite it in different ways. "
                "Example: if the user gives you 'how are you', return 4 ways to say 'how are you' — not answers to it. "
                "You MUST respond with ONLY this exact JSON format, nothing else:\n"
                "{\"results\": [\"version 1\", \"version 2\", \"version 3\", \"version 4\"]}\n"
                "Do NOT add any explanation, greeting, or text outside the JSON. "
                "Do NOT use markdown. Do NOT number the items. "
                "Each result must be a natural chat message that means the same thing as the input.\n\n"
                + GROUNDING_RULES
            )
            completion = safe_ai_call(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": text}
                ],
                max_tokens=400,
                use_json=True
            )
            reply = completion.choices[0].message.content.strip()
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
            return jsonify({"reply": reply})

        # ── MODE: summary ─────────────────────────────────────────────────────
        if mode == "summary":
            system = (
                "Summarize the following in 2 short sentences. "
                "Only use information present in the text. Do not add or infer anything.\n\n"
                + GROUNDING_RULES
            )
            completion = safe_ai_call(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": text}
                ],
                max_tokens=150
            )
            return jsonify({"reply": completion.choices[0].message.content.strip() or "..."})

        # ── MODE: greeting ────────────────────────────────────────────────────
        if mode == "greeting":
            system = (
                "Transform the message into 3–5 greeting style variations: casual, formal, friendly, slang. "
                "Only rephrase what the user wrote. Do not invent names or context.\n\n"
                + GROUNDING_RULES
            )
            completion = safe_ai_call(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": text}
                ],
                max_tokens=150
            )
            return jsonify({"reply": completion.choices[0].message.content.strip() or "..."})

        # ── MODE: chat (default) ──────────────────────────────────────────────
        if instructions:
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

        completion = safe_ai_call(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": text}
            ],
            max_tokens=150
        )
        reply = completion.choices[0].message.content.strip()
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
