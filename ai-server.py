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
    "https://chatflow-ai-o3e6.onrender.com",
    "https://chatflow.com",
    "https://backend-1-liqz.onrender.com",
    "https://testback-4sru.onrender.com",
    "https://backend-vz58.onrender.com",
    "https://chatflow-ai-o3e6.onrender.com"
    
])

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def safe_ai_call(messages, max_tokens, retries=2, use_json=False):
    for i in range(retries + 1):
        try:
            kwargs = dict(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.8,
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
    tone = data.get("tone", "")   # NEW — used only by mode == "help_me_write"

    try:
        system = "Reply in 1 short natural sentence like in a phone call."

        if mode == "summary":
            system = "Summarize in 2 short sentences."
        elif mode == "help_me_write":
            # tone now arrives packed as "Formal|length:Short|emoji:False"
            parts = tone.split("|") if tone else []
            tone_label = parts[0].strip() if parts else ""
            length = "Medium"
            use_emoji = False
            for p in parts[1:]:
                if p.startswith("length:"):
                    length = p.split(":", 1)[1].strip()
                if p.startswith("emoji:"):
                    use_emoji = p.split(":", 1)[1].strip().lower() == "true"

            tone_line = f"Tone: {tone_label}.\n" if tone_label else ""
            emoji_line = "You may use light, tasteful emoji.\n" if use_emoji else "Do not use any emoji.\n"

            if length == "Short":
                length_line = (
                    "Write EXACTLY 1 short sentence. Do not add details, reasons, or facts "
                    "that are not explicitly present in the user's prompt. If the prompt is vague, "
                    "keep the message equally vague rather than inventing specifics.\n"
                )
            elif length == "Long":
                length_line = (
                    "Write 4-6 sentences with more context and detail, but ONLY elaborate on what "
                    "is explicitly implied by the user's prompt — do not invent names, dates, numbers, "
                    "or events not present in the prompt.\n"
                )
            else:
                length_line = "Write 2-3 sentences.\n"

            system = (
                "You are helping someone write ONE chat message they are about to send. "
                "The user describes WHAT they want to say — you write it for them, as a natural "
                "message, not as a reply to them and not as an AI assistant. "
                f"{tone_line}{length_line}{emoji_line}"
                "Return ONLY the message text. No quotes, no explanation, no greeting like 'Sure, here is...'. "
                "Never state something as fact unless it was in the user's prompt."
            )
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
            system = f"""You are replying to chat messages like a real human.
USER-DEFINED BEHAVIOR:
{instructions}
RULES:
- Follow instructions strictly
- Keep replies short (1 sentence)
- Never sound like an AI assistant
- Do not add anything outside the scope of the user-defined behavior.
- Do not make assumptions about who the user is or what they want beyond what they wrote.
-Respond only using the information contained in the user's prompt. Rephrase, organize, and clarify the prompt creatively without adding new facts, assumptions, interpretations, examples, or information not explicitly present in the original tex

"""

        max_tokens = 400 if mode in ("ai_writer", "help_me_write") else 150

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
