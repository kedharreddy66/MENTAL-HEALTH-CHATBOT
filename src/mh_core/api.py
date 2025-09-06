from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .models import ChatIn, ChatOut, ChatState
from .crisis import contains_crisis_signal  # SUPPORT_TEXT intentionally unused in dev
from .ai_gateway import call_ollama_chat, SYSTEM_PROMPT
from .rag import retrieve_context

app = FastAPI(title="MH Chatbot (Free-form, Small Model)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn):
    """
    Free-form chat (dev):
    - No auto-welcome (empty input returns nothing)
    - Crisis bypassed for development (no helpline text)
    - Non-crisis: add RAG context and call local LLM
    """
    user = (body.message or "").strip()
    state = body.state or ChatState()

    if not user:
        return ChatOut(reply=None, state=state)

    # Crisis: in dev, do nothing special (bypass)
    if contains_crisis_signal(user):
        # In dev bypass, this won't trigger. Left here for future re-enable.
        return ChatOut(reply=None, state=state)

    # RAG context (approved snippets)
    context = retrieve_context(user)
    system = SYSTEM_PROMPT + (("\n\nAPPROVED CONTEXT:\n" + context) if context else "")
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    reply = call_ollama_chat(messages, temperature=0.3, top_p=0.9, max_tokens=120)

    # Filter accidental phone numbers in normal chat (kept for dev)
    low = (reply or "").lower()
    if any(w in low for w in [" call ", " phone ", "000", "1800", "13 "]):
        reply = "Here are a couple of ideas that might help right now."

    return ChatOut(reply=reply, state=state)

@app.get("/debug/model")
def debug_model():
    import http.client, json
    from .ai_gateway import OLLAMA_HOST, OLLAMA_PORT, OLLAMA_MODEL
    try:
        conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=3)
        conn.request("GET", "/api/tags")
        resp = conn.getresponse()
        tags = json.loads(resp.read().decode("utf-8", errors="ignore"))
        conn.close()
        available = any(t.get("model") == OLLAMA_MODEL for t in tags.get("models", []))
        return JSONResponse({"configured": OLLAMA_MODEL, "available": available, "tags": tags})
    except Exception as e:
        return JSONResponse({"configured": OLLAMA_MODEL, "available": False, "error": str(e)}, status_code=503)
