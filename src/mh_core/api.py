from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .models import ChatIn, ChatOut, ChatState
from .crisis import contains_crisis_signal, support_lines, looks_okay_response
from .ai_gateway import call_ollama_chat, SYSTEM_PROMPT
from .rag import retrieve_context
from .culture import normalize_for_retrieval
from pathlib import Path
import json as _json

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


@app.post("/reset")
def reset():
    """Resets the chat state for a new conversation."""
    fresh = ChatState()
    return JSONResponse({"state": fresh.model_dump()})

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

    # Crisis flow
    if state.crisis == "check":
        if looks_okay_response(user):
            state.crisis = "done"
            return ChatOut(
                reply="Thanks for letting me know. I'm here if you want to talk more.",
                state=state,
            )
        # Show helplines
        lines = support_lines()
        state.crisis = "done"
        msgs = [
            "I am really glad you told me; getting support matters.",
        ]
        if lines:
            msgs.append("If you want to talk to someone now, here are some options:")
            msgs.extend(lines)
        else:
            msgs.append("If you want to talk to someone now, please reach out to a local helpline or emergency services.")
        return ChatOut(mode="crisis", messages=msgs, state=state)

    if contains_crisis_signal(user):
        # Ask permission to talk about it; do not show numbers yet
        state.crisis = "check"
        return ChatOut(
            mode="crisis",
            messages=[
                "Would you like to talk about that? I can share some support options if you want.",
            ],
            state=state,
        )

    # Optional local style guide (appended to system prompt if present)
    style_append = ""
    try:
        sg_path = Path(__file__).resolve().parents[2] / "content" / "style_guide_local.json"
        if sg_path.exists():
            sg = _json.loads(sg_path.read_text(encoding="utf-8"))
            style_append = (sg.get("append") or "").strip()
    except Exception:
        style_append = ""

    # Mode toggles (env)
    import os as _os
    plain_mode = (_os.getenv("PLAIN_ENGLISH_MODE", "true").lower() in ("1", "true", "yes"))
    fast_mode = (_os.getenv("FAST_MODE", "true").lower() in ("1", "true", "yes"))
    if body.fast is not None:
        fast_mode = bool(body.fast)

    # Lexicon: help the model interpret Aboriginal English while replying in plain English
    norm_user, lex_notes = normalize_for_retrieval(user)

    # RAG context (approved snippets)
    context = "" if fast_mode else retrieve_context(norm_user)
    system = SYSTEM_PROMPT
    if style_append and plain_mode:
        system += "\n\nLOCAL STYLE GUIDE:\n" + style_append
    if lex_notes:
        system += "\n\nLEXICON NOTES (user terms):\n- " + "\n- ".join(lex_notes)
    if context:
        system += "\n\nAPPROVED CONTEXT:\n" + context
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    max_toks = 60 if fast_mode else 90
    reply = call_ollama_chat(messages, temperature=0.25 if fast_mode else 0.3, top_p=0.9, max_tokens=max_toks)

    # Filter accidental phone numbers in normal chat (not applied in crisis mode)
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

