from flask import Flask, request, jsonify
from groq import Groq
from flask_cors import CORS
import os
import time
import json
app = Flask(__name__)
CORS(app, origins=[
    "https://chatflow-ai-1.onrender.com",
    "https://chatflow.com",
    "https://backend-1-liqz.onrender.com"
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
                timeout=20
            )
            if use_json:
                kwargs["response_format"] = {"type": "json_object"}
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            if i == retries:
                raise e
            time.sleep(0.5)

@app.route("/ai", methods=["POST"])
 reply = completion.choices[0].message.content.strip()

        # For ai_writer, validate the JSON — if broken, rebuild it
        if mode == "ai_writer":
            try:
                parsed = json.loads(reply)
                if not isinstance(parsed.get("results"), list) or len(parsed["results"]) < 2:
                    raise ValueError("bad results")
            except Exception:
                # Model returned plain text — wrap it into 4 variations manually
                clean = reply.replace('"', "'").strip()
                fallback = {
                    "results": [
                        clean,
                        clean + "!",
                        clean + " 😊",
                        clean + ", what do you think?"
                    ]
                }
                return jsonify({"reply": json.dumps(fallback)})

        return jsonify({"reply": reply or "..."})

    try:
        # DEFAULT SYSTEM PROMPT
        system = "Reply in 1 short natural sentence like in a phone call."

        if mode == "summary":
            system = "Summarize in 2 short sentences."
        elif mode == "ai_writer":
    system = (
        "You are a message suggestion generator. "
        "The user will give you a topic or message. "
        "You MUST respond with ONLY this exact JSON format, nothing else:\n"
        "{\"results\": [\"suggestion 1\", \"suggestion 2\", \"suggestion 3\", \"suggestion 4\"]}\n"
        "Do NOT add any explanation, greeting, or text outside the JSON. "
        "Do NOT use markdown. Do NOT number the items. "
        "Each suggestion must be a complete natural chat message."
    )
        elif mode == "greeting":
            system = (
                "Transform the message into different greeting styles. "
                "Give 3-5 variations like casual, formal, friendly, slang."
            )

        # CUSTOM AI MODE — skip for ai_writer to preserve JSON format
        if instructions and instructions.strip() and mode != "ai_writer":
            system = f"""You are replying to chat messages like a real human.
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
            max_tokens=max_tokens,
            use_json=(mode == "ai_writer")
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
