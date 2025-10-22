import http.client
import json
import os

from .ai_gateway import call_ollama_chat


# Read the API key from the standard environment variable name.
# Never hard-code or bake keys into source.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def call_openai_chat(messages, temperature=0.3, top_p=0.9, max_tokens=90):
    """
    Calls OpenAI chat completions API. Requires OPENAI_API_KEY.
    Returns text content on success or raises on HTTP errors.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": float(temperature),
        "top_p": float(top_p),
        "max_tokens": int(max_tokens),
    }
    body = json.dumps(payload)
    conn = http.client.HTTPSConnection("api.openai.com", 443, timeout=60)
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    conn.request("POST", "/v1/chat/completions", body=body, headers=headers)
    resp = conn.getresponse()
    data = resp.read().decode("utf-8", errors="ignore")
    conn.close()
    if resp.status >= 400:
        raise RuntimeError(f"OpenAI HTTP {resp.status}: {data[:200]}")
    try:
        obj = json.loads(data)
        choice = (obj.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        return (msg.get("content") or "").strip() or "..."
    except Exception:
        return "Sorry, I had trouble thinking just now."


def generate(messages, temperature=0.3, top_p=0.9, max_tokens=90):
    """
    Unified generation:
    - If OPENAI_API_KEY is available, use OpenAI; otherwise use Ollama.
    - If OpenAI errors, fall back to Ollama.
    """
    if OPENAI_API_KEY:
        try:
            return call_openai_chat(messages, temperature=temperature, top_p=top_p, max_tokens=max_tokens)
        except Exception:
            pass
    return call_ollama_chat(messages, temperature=temperature, top_p=top_p, max_tokens=max_tokens)
