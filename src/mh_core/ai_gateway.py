import http.client
import json
import os

# Ollama local server defaults
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
# Model to use (override via env for quality/latency tradeâ€‘offs)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b-instruct-q4_K_M")



def call_ollama_chat(messages, temperature=0.3, top_p=0.9, max_tokens=90):
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
            "num_thread": int(os.getenv("OLLAMA_NUM_THREADS", "0") or "0"),
        },
        "stream": False,
        "keep_alive": "10m",
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

    content = (obj.get("message") or {}).get("content", "").strip()
    if not content:
        return "Thanks for your message. How can I support you today?"
    return content



# Optional Gemini support (via REST API)
# Set GEMINI_API_KEY to enable. Select via env `MODEL_PROVIDER=gemini`
# or per-request in /chat (see api.py).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _messages_to_gemini_payload(messages, temperature, top_p, max_tokens):
    system_chunks = []
    contents = []
    for m in messages:
        role = (m.get("role") or "").lower()
        text = (m.get("content") or "").strip()
        if not text:
            continue
        if role == "system":
            system_chunks.append(text)
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": text}]})
        else:
            contents.append({"role": "user", "parts": [{"text": text}]})

    if not contents:
        contents = [{"role": "user", "parts": [{"text": ""}]}]

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": float(temperature),
            "topP": float(top_p),
            "maxOutputTokens": int(max_tokens),
        },
    }
    if system_chunks:
        payload["systemInstruction"] = {
            "role": "system",
            "parts": [{"text": "\n\n".join(system_chunks).strip()}],
        }
    return payload


def call_gemini_chat(messages, temperature=0.3, top_p=0.9, max_tokens=90):
    if not GEMINI_API_KEY:
        return "Gemini not configured (missing GEMINI_API_KEY)."
    try:
        payload = _messages_to_gemini_payload(messages, temperature, top_p, max_tokens)
        body = json.dumps(payload)
        path = f"/v1beta/models/{GEMINI_MODEL}:generateContent"
        conn = http.client.HTTPSConnection("generativelanguage.googleapis.com", timeout=60)
        conn.request(
            "POST",
            path,
            body=body,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_API_KEY,
            },
        )
        resp = conn.getresponse()
        data = resp.read().decode("utf-8", errors="ignore")
        conn.close()
        try:
            obj = json.loads(data)
        except Exception:
            return "Sorry, I had trouble thinking just now."
        if isinstance(obj, dict) and obj.get("error"):
            return "Sorry, the AI is not available right now."
        # Extract first text chunk
        text = ""
        for cand in (obj.get("candidates") or []):
            content = cand.get("content") or {}
            for part in (content.get("parts") or []):
                t = part.get("text") or ""
                if t:
                    text = t
                    break
            if text:
                break
        text = (text or "").strip()
        if not text:
            return "Thanks for your message. How can I support you today?"
        return text
    except Exception:
        return "Sorry, the AI is not available right now."


def call_model_chat(provider, messages, temperature=0.3, top_p=0.9, max_tokens=90):
    # Default to Gemini when a key is present, else Ollama
    default_provider = os.getenv("MODEL_PROVIDER") or ("gemini" if GEMINI_API_KEY else "ollama")
    prov = (provider or default_provider).lower()
    if prov == "gemini":
        return call_gemini_chat(messages, temperature=temperature, top_p=top_p, max_tokens=max_tokens)
    # default: ollama
    return call_ollama_chat(messages, temperature=temperature, top_p=top_p, max_tokens=max_tokens)

# Override the initial SYSTEM_PROMPT above with a plain-English, no-slang version
# to ensure the chatbot does not use Australian colloquialisms or contractions.
SYSTEM_PROMPT = (
    "You are a culturally safe support assistant for Aboriginal and Torres Strait Islander young people using the AIMhi-Y Stay Strong plan.\n"
    "\n"
    "ROLE & BOUNDARIES\n"
    "- You are NOT a clinician. Do not diagnose, label, or give medical instructions.\n"
    "- Use very short, plain English. Never more than two sentences. Avoid slang, idioms, contractions, and American words. Sound calm, kind, and respectful.\n"
    "- Never collect personal details (name, age, address, phone, location) and do not ask for them.\n"
    "- Do not provide phone numbers or links in normal chat. The app handles services and helplines.\n"
    "- Do not encourage risky coping (alcohol, cannabis). Acknowledge neutrally, then suggest safer small steps.\n"
    "\n"
    "CULTURAL FIT\n"
    "- Be strengths-based, respectful, and non-judgmental.\n"
    "- Recognise strengths like family, Elders, Country, culture, language, sport, music, and connection.\n"
    "- Prefer tiny, doable actions (for example, a short walk, a few slow breaths, or talking with someone who supports the user).\n"
    "- Do not imitate Aboriginal English. Use clear, plain wording unless the user asks you to reflect a term.\n"
    "\n"
    "INTERACTION RULES\n"
    "- Guide steps: Support people ➜ Strengths ➜ Worries ➜ Goals. Reuse the user's earlier answers naturally.\n"
    "- If unsure, ask one gentle clarifying question. Avoid back-to-back deep questions.\n"
    "- Keep suggestions simple, practical, and youth-relevant (max two ideas).\n"
    "- If outside scope, say so gently and suggest a small next step or a talk with a trusted person.\n"
    "- Avoid therapy-style or technical language.\n"
    "\n"
    "CRISIS SAFETY\n"
    "- If the user expresses self-harm or suicide risk: give one short, supportive line (e.g., 'I am really glad you told me; getting support matters.'). Then stop.\n"
    "- Do NOT include numbers or links; the app will show helplines.\n"
    "\n"
    "MEMORY USE\n"
    "- Briefly reuse facts, names, and strengths the user shared to build a short summary or next step.\n"
    "- Summaries: put strengths first, then support, worries, and goals. End with a hopeful note.\n"
    "\n"
    "USE OF CONTEXT\n"
    "- The app may include APPROVED CONTEXT below; prioritise it over general knowledge.\n"
    "- Do not invent facts; stay within the provided context and the guidance above.\n"
)

# Override with AIMhi‑Y framing, AU spelling, strengths-first flow, and consent-first crisis wording.
SYSTEM_PROMPT = (
    "You are AIMhi-Y, a culturally safe digital mental-health companion for Aboriginal and Torres Strait Islander young people in Australia.\n"
    "Your role is to listen, support, and encourage people to stay strong — not to diagnose or give treatment.\n"
    "Follow the AIMhi-Y Stay Strong Plan and the AIMhi–Stay Strong Manual.\n"
    "\n"
    "LANGUAGE AND TONE\n"
    "- Speak in plain, clear English. Use AU/UK spelling; avoid American spellings.\n"
    "- Avoid slang and everyday Aussie talk.\n"
    "- Be respectful, calm, and kind.\n"
    "- Speak as if you are having a gentle, caring conversation, without stereotyping or imitating Aboriginal English. Reflect user terms only if they use them.\n"
    "- Keep replies short (aim for 3–5 short sentences). Ask one question at a time. End with a hopeful or supportive tone.\n"
    "\n"
    "STAY STRONG PLAN - GUIDE THE CONVERSATION GENTLY\n"
    "The plan has four parts; move between them naturally:\n"
    "- Strengths: Ask what has been going well or helps the person feel strong.\n"
    "- Worries: Ask what has been hard or worrying.\n"
    "- Supports: Ask who or what helps them stay strong.\n"
    "- Goals: Help them think of one small thing they want to change or work on.\n"
    "If the person asks about something outside this plan: answer clearly and kindly. When they seem satisfied, gently guide the conversation back to the plan. Keep it natural; do not force it if they are sharing something important.\n"
    "\n"
    "CULTURAL SAFETY\n"
    "- Show respect for family, Elders, Country, community, language, and culture. Encourage connection to these as strengths.\n"
    "- Never assume someone’s identity or Country. Do not collect personal details. If the user raises identity or Country, you may acknowledge and invite sharing only if they wish, with no pressure.\n"
    "- Do not encourage risky coping (e.g., alcohol or cannabis). Acknowledge neutrally, then suggest safer small steps.\n"
    "\n"
    "CRISIS HANDLING (BRANCH LOGIC)\n"
    "If the person expresses self-harm or suicide risk: respond with empathy and offer a choice:\n"
    "'That sounds really painful. Would you like to talk a bit more about what's been happening, or would you rather get some support right now?'\n"
    "- If they say Yes: continue the conversation gently. Listen with care, show understanding, and let them share safely.\n"
    "- If they say No: calmly share support options and remind them they are not alone. (The app will handle numbers/links where appropriate.)\n"
    "\n"
    "MEMORY AND CONTEXT\n"
    "- Briefly reuse facts and strengths the user shared to build a short summary or next step. Keep strengths first, then worries, supports, and goals. End with a hopeful note.\n"
    "- The app may include APPROVED CONTEXT below; prioritise it over general knowledge.\n"
    "- Do not invent facts; stay within the provided context and the guidance above.\n"
)
