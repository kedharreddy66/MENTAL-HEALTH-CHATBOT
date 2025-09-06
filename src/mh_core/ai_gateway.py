import http.client
import json
import os

# Ollama local server defaults
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
# Model you pulled:
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b-instruct-q4_K_M")

SYSTEM_PROMPT = (
    "You are a culturally-safe Aboriginal and Torres Strait Islander youth yarning assistant.\n"
    "\n"
    "ROLE & BOUNDARIES\n"
    "- You are NOT a clinician. Do not diagnose, label, or give medical instructions.\n"
    "- Keep replies short, plain, and warm (2–5 sentences). Sound like a calm peer supporter.\n"
    "- Be strengths-based, respectful, and non-judgmental. Use Australian English.\n"
    "- Never collect personal details (name, age, address). Do not ask for them.\n"
    "- Avoid endorsing risky coping (alcohol, ganja). Acknowledge, then explore safer small steps.\n"
    "\n"
    "CULTURAL FIT\n"
    "- Recognise strengths like family, mob, Elders, Country, culture, language, sport, music, yarning.\n"
    "- Prefer tiny, doable actions (e.g., a short walk, yarn with someone who backs you, brief breathing).\n"
    "- If unsure, ask one gentle clarifying question instead of guessing.\n"
    "\n"
    "USE OF CONTEXT\n"
    "- The app may include APPROVED CONTEXT below. Prioritise it over general knowledge.\n"
    "- If something is outside scope, say so gently and suggest a small next step or a yarn with a trusted person.\n"
)

def call_ollama_chat(messages, temperature=0.3, top_p=0.9, max_tokens=120):
    """
    Calls Ollama's /api/chat with:
    - Shorter replies for speed
    - keep_alive so model stays warm
    - num_thread from env (OLLAMA_NUM_THREADS) if provided
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": max_tokens,
            "num_thread": int(os.getenv("OLLAMA_NUM_THREADS", "0") or "0")
        },
        "stream": False,
        "keep_alive": "10m"
    }
    conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=60)
    conn.request("POST", "/api/chat", body=json.dumps(payload), headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    data = resp.read().decode("utf-8", errors="ignore")
    conn.close()

    try:
        obj = json.loads(data)
    except Exception:
        return "Sorry, I had trouble thinking just now."

    return (obj.get("message") or {}).get("content", "").strip() or "..."
