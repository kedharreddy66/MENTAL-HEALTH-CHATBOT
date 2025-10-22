import os
print("DEBUG: api.py is being executed!")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, Response
from .models import (
    ChatIn, ChatOut, ChatState,
    SignupIn, LoginIn, TokenOut,
    SignupRequestIn, SignupVerifyIn,
    LoginRequestIn, LoginVerifyIn,
)
from .crisis import contains_crisis_signal, support_lines, looks_okay_response
from .ai_gateway import SYSTEM_PROMPT, call_ollama_chat, call_model_chat
from .rag import retrieve_context
from .sentiment import analyze_sentiment
from .culture import normalize_for_retrieval
from pathlib import Path
import http.client as _http
from fastapi import Request
from . import auth as _auth
from urllib.parse import urlencode, parse_qs
import json as _json
# Load .env variables (if present) into process env for SMTP and other settings
try:
    from .env import load_dotenv_if_present as _load_env
    _load_env()
except Exception:
    pass

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


@app.get("/")
def index():
    """Start on login/auth page to require authentication first."""
    return RedirectResponse(url="/auth.html")


@app.get("/chat.html")
def chat_html():
    """Serve the static chat.html file located at the project root."""
    root_dir = Path(__file__).resolve().parents[2]
    html_path = root_dir / "chat.html"
    if not html_path.exists():
        # Fallback: provide a helpful message if the file is missing
        return JSONResponse({"error": "chat.html not found at project root"}, status_code=404)
    return FileResponse(
        str(html_path),
        media_type="text/html",
        headers={
            # Prevent mobile caches from serving stale JS/URLs
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/auth.html")
def combined_auth_html():
    root_dir = Path(__file__).resolve().parents[2]
    # Serve the canonical root-level auth.html only (override removed)
    html_path = root_dir / "auth.html"
    if not html_path.exists():
        return JSONResponse({"error": "auth.html not found at project root"}, status_code=404)
    return FileResponse(str(html_path), media_type="text/html")


# design asset route removed (no external design folder)


@app.get("/login.html")
def login_html():
    root_dir = Path(__file__).resolve().parents[2]
    html_path = root_dir / "login.html"
    if not html_path.exists():
        return JSONResponse({"error": "login.html not found at project root"}, status_code=404)
    return FileResponse(str(html_path), media_type="text/html")


@app.get("/signup.html")
def signup_html():
    root_dir = Path(__file__).resolve().parents[2]
    html_path = root_dir / "signup.html"
    if not html_path.exists():
        return JSONResponse({"error": "signup.html not found at project root"}, status_code=404)
    return FileResponse(str(html_path), media_type="text/html")


def _abs_url(req: Request, path: str) -> str:
    try:
        proto = req.headers.get("x-forwarded-proto") or req.url.scheme
        host = req.headers.get("x-forwarded-host") or req.headers.get("host") or req.url.netloc
        base = f"{proto}://{host}"
        return base + path
    except Exception:
        return str(req.url).rsplit('/',1)[0] + path


@app.get("/auth/google/start", include_in_schema=False)
def google_start(req: Request):
    import os as _os
    cid = _os.getenv("GOOGLE_CLIENT_ID")
    if not cid:
        return JSONResponse({"error": "GOOGLE_CLIENT_ID not set"}, status_code=400)
    state = _auth.oauth_new_state("google")
    redirect_uri = _os.getenv("GOOGLE_REDIRECT_URI") or _abs_url(req, "/auth/google/callback")
    params = {
        "client_id": cid,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url=url)


@app.get("/auth/google/callback", include_in_schema=False)
def google_callback(req: Request):
    import os as _os
    q = parse_qs(req.url.query)
    code = (q.get("code") or [None])[0]
    state = (q.get("state") or [None])[0]
    if not code or not state or not _auth.oauth_consume_state(state, "google"):
        return JSONResponse({"error": "Invalid state or code"}, status_code=400)
    cid = _os.getenv("GOOGLE_CLIENT_ID")
    csec = _os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = _os.getenv("GOOGLE_REDIRECT_URI") or _abs_url(req, "/auth/google/callback")
    if not (cid and csec):
        return JSONResponse({"error": "Google OAuth not configured"}, status_code=400)
    try:
        body = urlencode({
            "code": code,
            "client_id": cid,
            "client_secret": csec,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        conn = _http.HTTPSConnection("oauth2.googleapis.com", timeout=10)
        conn.request("POST", "/token", body=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
        resp = conn.getresponse()
        data = _json.loads(resp.read().decode("utf-8", errors="ignore"))
        conn.close()
        access = data.get("access_token")
        if not access:
            return JSONResponse({"error": "Token exchange failed", "detail": data}, status_code=400)
        # Get userinfo
        conn = _http.HTTPSConnection("openidconnect.googleapis.com", timeout=10)
        conn.request("GET", "/v1/userinfo", headers={"Authorization": f"Bearer {access}"})
        resp = conn.getresponse()
        u = _json.loads(resp.read().decode("utf-8", errors="ignore"))
        conn.close()
        email = (u.get("email") or "").lower()
        if not email:
            return JSONResponse({"error": "No email from Google"}, status_code=400)
        user = _auth.upsert_user_by_email(email)
        token = _auth.create_token(user["id"], user["username"])
        html = f"""<!doctype html><html><body>
<script>
localStorage.setItem('mh_token','{token}');
localStorage.setItem('mh_user','{user['username']}');
window.location='/chat.html';
</script>
OK</body></html>"""
        return Response(content=html, media_type="text/html")
    except Exception as e:
        return JSONResponse({"error": "OAuth error", "detail": str(e)}, status_code=500)


@app.get("/auth/apple/start", include_in_schema=False)
def apple_start():
    return JSONResponse({"error": "Apple Sign-In requires configuration; see README"}, status_code=501)


@app.get("/auth/apple/callback", include_in_schema=False)
def apple_callback():
    return JSONResponse({"error": "Apple Sign-In not yet configured"}, status_code=501)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    # Return an empty 204 with no body to avoid Content-Length issues
    return Response(status_code=204)


@app.post("/reset")
def reset(req: Request):
    """Resets the chat state for a new conversation (requires auth)."""
    payload = _get_auth_payload(req)
    if not payload:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    fresh = ChatState()
    return JSONResponse({"state": fresh.model_dump()})


def _get_auth_payload(req: Request):
    try:
        auth = req.headers.get("authorization") or req.headers.get("Authorization") or ""
        if not auth.lower().startswith("bearer "):
            return None
        token = auth.split(" ", 1)[1].strip()
        return _auth.verify_token(token)
    except Exception:
        return None


 


@app.post("/signup", response_model=TokenOut)
async def signup(body: SignupIn):
    try:
        user = _auth.create_user(body.username, body.password, getattr(body, 'email', None), email_verified=bool(getattr(body, 'email', None)))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    token = _auth.create_token(user["id"], user["username"])
    return TokenOut(token=token, user=user)


@app.post("/login", response_model=TokenOut)
async def login(body: LoginIn):
    """Password login: supports username+password or email+password.
    For OTP, use /auth/login/request and /auth/login/verify.
    """
    # Guard: OTP flow should use dedicated endpoints
    if getattr(body, 'email', None) and not getattr(body, 'password', None):
        return JSONResponse({"error": "Use OTP login endpoints"}, status_code=400)
    user = None
    # Try username + password first when provided
    if getattr(body, 'username', None) and getattr(body, 'password', None):
        user = _auth.authenticate(body.username, body.password)
    # Fallback: email + password (find account by email and verify password)
    if not user and getattr(body, 'email', None) and getattr(body, 'password', None):
        user = _auth.authenticate_by_email(body.email, body.password)
    if not user:
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)
    token = _auth.create_token(user["id"], user["username"])
    return TokenOut(token=token, user=user)


# OTP signup/login endpoints
def _client_ip(req: Request) -> str:
    xf = req.headers.get("x-forwarded-for") or req.headers.get("X-Forwarded-For")
    if xf:
        return xf.split(",")[0].strip()
    return getattr(getattr(req, 'client', None), 'host', '') or ''


@app.post("/auth/signup/request")
async def auth_signup_request(body: SignupRequestIn, req: Request):
    try:
        out = _auth.request_signup(body.email, body.username, _client_ip(req))
        return JSONResponse(out)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/auth/signup/verify", response_model=TokenOut)
async def auth_signup_verify(body: SignupVerifyIn):
    try:
        user = _auth.verify_signup(body.email, body.username, body.code, getattr(body, 'password', None))
        token = _auth.create_token(user["id"], user["username"])  # default ttl
        return TokenOut(token=token, user=user)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/auth/login/request")
async def auth_login_request(body: LoginRequestIn, req: Request):
    try:
        out = _auth.request_login(body.email, _client_ip(req))
        return JSONResponse(out)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/auth/otp/status")
async def auth_otp_status(email: str):
    try:
        return JSONResponse(_auth.otp_status(email))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/auth/dev/otp")
async def auth_dev_otp(email: str):
    import os as _os
    if not (_os.getenv("DEV_OTP_DEBUG") in ("1","true","TRUE","yes","YES")):
        return JSONResponse({"error": "Not enabled"}, status_code=403)
    code = _auth._read_dev_latest_otp(email)
    if not code:
        return JSONResponse({"error": "No OTP found"}, status_code=404)
    return JSONResponse({"email": email, "code": code})


@app.post("/auth/login/verify", response_model=TokenOut)
async def auth_login_verify(body: LoginVerifyIn):
    try:
        user = _auth.verify_login(body.email, body.code)
        if not user:
            return JSONResponse({"error": "Invalid code or user not found"}, status_code=401)
        token = _auth.create_token(user["id"], user["username"])  # default ttl
        return TokenOut(token=token, user=user)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/state")
async def get_state(req: Request):
    payload = _get_auth_payload(req)
    if not payload:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    st = _auth.read_state(payload["sub"]) or ChatState().model_dump()
    return JSONResponse({"state": st})

@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, req: Request):
    """
    Free-form chat (dev):
    - No auto-welcome (empty input returns nothing)
    - Crisis bypassed for development (no helpline text)
    - Non-crisis: add RAG context and call local LLM
    """
    user = (body.message or "").strip()
    payload = _get_auth_payload(req)
    # Hard gate: require auth for chat
    if not payload:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if body.state is None and payload:
        saved = _auth.read_state(payload["sub"]) or None
        state = ChatState(**saved) if saved else ChatState()
    else:
        state = body.state or ChatState()

    if not user:
        return ChatOut(reply=None, state=state)

    # Sentiment (soft signal only, no persistence)
    sent_label, sent_score = analyze_sentiment(user)

    # Crisis flow: first ask consent to talk; on "no" show support options
    def _looks_yes(text: str) -> bool:
        low = (text or "").strip().lower()
        return any(w in low for w in ["yes", "ye", "yeah", "yep", "ok", "okay", "sure", "please", "i do", "i want to"]) and not any(n in low for n in ["nope", "nah", "no ", " not now", "later", "don't", "dont", "do not"])

    def _looks_no(text: str) -> bool:
        low = (text or "").strip().lower()
        return any(w in low for w in ["no", "nah", "nope", "not now", "later", "maybe later", "not really", "no thanks", "no thank you"]) and not any(y in low for y in ["yes", "yeah", "yep"]) 

    # If already in crisis check, branch on yes/no
    if state.crisis == "check":
        if _looks_yes(user):
            reply = "Thank you for trusting me. Let us yarn a bit about what has been happening."
            out = ChatOut(reply=reply, state=state)
            if payload:
                try:
                    _auth.write_state(payload["sub"], state.model_dump())
                except Exception:
                    pass
            return out
        if _looks_no(user):
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
            reply_joined = "\n".join(msgs)
            out = ChatOut(mode="crisis", messages=msgs, reply=reply_joined, tool="route_to_support", state=state)
            if payload:
                try:
                    _auth.write_state(payload["sub"], state.model_dump())
                except Exception:
                    pass
            return out
        # Unclear reply: gently ask again with the same choice wording
        reply = "Would you like to talk a bit more about what has been happening, or would you rather get some support right now?"
        out = ChatOut(reply=reply, state=state)
        if payload:
            try:
                _auth.write_state(payload["sub"], state.model_dump())
            except Exception:
                pass
        return out

    # New crisis trigger: ask consent to talk first
    if contains_crisis_signal(user):
        state.crisis = "check"
        reply = "That sounds really painful. Would you like to talk a bit more about what has been happening, or would you rather get some support right now?"
        out = ChatOut(reply=reply, state=state)
        if payload:
            try:
                _auth.write_state(payload["sub"], state.model_dump())
            except Exception:
                pass
        return out

    

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
    # Fast mode removed: always use full retrieval + normal generation settings

    # Lexicon: help the model interpret Aboriginal English while replying in plain English
    norm_user, lex_notes = normalize_for_retrieval(user)

    # RAG context (approved snippets)
    context = retrieve_context(norm_user)
    system = SYSTEM_PROMPT
    if style_append and plain_mode:
        system += "\n\nLOCAL STYLE GUIDE:\n" + style_append
    # Include a brief sentiment signal to guide tone (never label the user clinically)
    if sent_label:
        system += "\n\nSENTIMENT SIGNAL: The user's tone seems {}. Respond gently and keep language simple.".format(sent_label)
    if lex_notes:
        system += "\n\nLEXICON NOTES (user terms):\n- " + "\n- ".join(lex_notes)
    if context:
        system += "\n\nAPPROVED CONTEXT:\n" + context
    # Build message list with short memory from state
    messages = [{"role": "system", "content": system}]
    try:
        hist = getattr(state, 'history', []) or []
        # keep last 8 exchanges (16 turns) to control context size
        trimmed = hist[-16:]
        for m in trimmed:
            role = m.get("role")
            content = m.get("content")
            if role in ("user","assistant") and isinstance(content, str) and content:
                messages.append({"role": role, "content": content})
    except Exception:
        pass
    messages.append({"role": "user", "content": user})

    max_toks = 320
    # Step-by-step flow helpers
    def _split_items(text: str) -> list[str]:
        if not text:
            return []
        low = text.strip()
        # Split on commas or ' and '
        raw = []
        for chunk in low.replace(" and ", ",").split(","):
            t = chunk.strip()
            if t:
                raw.append(t)
        # Deduplicate while preserving order
        seen, out = set(), []
        for r in raw:
            if r.lower() not in seen:
                seen.add(r.lower())
                out.append(r)
        return out[:4]

    def _limit_sentences(text: str, max_sentences: int = 5) -> str:
        s = (text or "").strip()
        if not s:
            return s
        parts = []
        cur = ""
        for ch in s:
            cur += ch
            if ch in ".!?":
                if cur.strip():
                    parts.append(cur.strip())
                cur = ""
                if len(parts) >= max_sentences:
                    break
        if cur.strip() and len(parts) < max_sentences:
            parts.append(cur.strip())
        if not parts:
            return s
        return " ".join(parts[:max_sentences])

    # # Guided Stay Strong plan: support -> strengths -> worries -> goals
    # if state.step == "support":
    #     items = _split_items(user)
    #     if items:
    #         state.support = ", ".join(items)
    #     state.step = "strengths"
    #     guided = f"Thanks. Good to have {state.support or 'people around you'}. "
    #     guided += "What are your strengths, like things you are proud of or good at?"
    #     return ChatOut(reply=_two_sentences(guided), state=state)

    # if state.step == "strengths":
    #     items = _split_items(user)
    #     if items:
    #         state.strengths.extend([i for i in items if i not in state.strengths])
    #     state.step = "worries"
    #     s_preview = ", ".join(state.strengths[:2]) or "your strengths"
    #     guided = f"Nice. {s_preview} are solid strengths."
    #     guided += " What is making life tough right now?"
    #     return ChatOut(reply=_two_sentences(guided), state=state)

    # if state.step == "worries":
    #     items = _split_items(user)
    #     if items:
    #         state.worries.extend([i for i in items if i not in state.worries])
    #     state.step = "goal"
    #     w_one = state.worries[0] if state.worries else "that"
    #     guided = f"I hear you about {w_one}."
    #     guided += " Let us pick one small goal you want to try."
    #     return ChatOut(reply=_two_sentences(guided), state=state)

    # if state.step == "goal":
    #     # Take first short phrase as goal
    #     g = user.strip()
    #     if len(g) > 120:
    #         g = g[:120].rsplit(" ", 1)[0]
    #     state.goal = g
    #     state.step = "done"
    #     # Short positive summary in required order: strengths -> support -> worries -> goal
    #     strengths = ", ".join(state.strengths[:2]) or "your strengths"
    #     support = state.support or "your supports"
    #     worries = ", ".join(state.worries[:1]) or "your worries"
    #     guided = f"Here is your plan: Strengths: {strengths}. Support: {support}. Worries: {worries}. Goal: {state.goal}."
    #     guided += " You can do this."
    #     return ChatOut(reply=_two_sentences(guided), state=state)

    # Free-form model reply
    try:
        provider = getattr(body, 'provider', None) or None
        reply = call_model_chat(
            provider,
            messages,
            temperature=0.2,
            top_p=0.9,
            max_tokens=max_toks,
        )
    except Exception:
        # Keep HTTP 200 so the client UI can show a friendly message
        reply = "Sorry, the AI is not available right now. Please try again later."

    # Repair and normalize very short or empty replies
    def _is_greeting(text: str) -> bool:
        t = (text or "").strip().lower()
        return t in {"hi", "hello", "hey", "yo", "hiya", "hullo"} or t.startswith("hello") or t.startswith("hi ") or t.startswith("hey ")

    def _repair_reply(user_text: str, model_reply: str) -> str:
        r = (model_reply or "").strip()
        if not r or r in {"...", "…"} or len(r) < 3:
            if _is_greeting(user_text):
                return "Hello. How can I support you today?"
            return "Thanks for your message. How can I support you today?"
        # If reply ends mid-thought (no sentence end), add a period and, if dangling, append a short supportive line.
        if r[-1] not in ".!?":
            r = r + "."
        dangling_tokens = {"your", "my", "their", "our", "his", "her", "to", "and", "or", "but", "because", "so"}
        last_word = r.rstrip(".!? ").split()[-1].lower() if r.split() else ""
        if last_word in dangling_tokens or len(r.split()) < 3:
            r = r + " I am here to listen."
        return r

    reply = _repair_reply(user, reply)
    # Enforce max sentence count for normal chat (align with style guide)
    reply = _limit_sentences(reply, max_sentences=5)

    # Filter accidental phone numbers in normal chat (not applied in crisis mode)
    # Only trigger on actual numbers/links, not the generic word "phone".
    import re as _re
    def _contains_contact_number(text: str) -> bool:
        t = text or ""
        if _re.search(r"\b(000|112)\b", t):
            return True
        if _re.search(r"\b1(?:300|800)\b", t):  # 1300 / 1800
            return True
        if _re.search(r"\b13\s?\d{2}\s?\d{2}\b", t):  # e.g., 13 11 14
            return True
        if _re.search(r"\+?\d[\d\s-]{7,}", t):  # generic long digit sequences
            return True
        return False

    low = (reply or "").lower()
    if _contains_contact_number(reply) or ("call" in low and _contains_contact_number(reply)) or ("phone" in low and _contains_contact_number(reply)):
        reply = "Here are a couple of ideas that might help right now."

    # Append to memory and cap length
    try:
        hist = getattr(state, 'history', []) or []
        hist.append({"role": "user", "content": user})
        hist.append({"role": "assistant", "content": reply or ""})
        if len(hist) > 40:  # cap total turns
            hist = hist[-40:]
        state.history = hist
    except Exception:
        pass
    out = ChatOut(reply=reply, state=state)
    if payload:
        try:
            _auth.write_state(payload["sub"], state.model_dump())
        except Exception:
            pass
    return out

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


@app.get("/debug/providers")
def debug_providers():
    import http.client, json, os
    from .ai_gateway import OLLAMA_HOST, OLLAMA_PORT, OLLAMA_MODEL, GEMINI_API_KEY, GEMINI_MODEL
    out = {"ollama": {"configured": OLLAMA_MODEL, "available": False}, "gemini": {"configured": None, "available": False}}
    # Ollama check via /api/tags
    try:
        conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=3)
        conn.request("GET", "/api/tags")
        resp = conn.getresponse()
        tags = json.loads(resp.read().decode("utf-8", errors="ignore"))
        conn.close()
        out["ollama"]["available"] = any(t.get("model") == OLLAMA_MODEL for t in tags.get("models", []))
    except Exception:
        out["ollama"]["available"] = False
    # Gemini: treat as available if API key present
    if GEMINI_API_KEY:
        out["gemini"]["configured"] = GEMINI_MODEL
        out["gemini"]["available"] = True
    return JSONResponse(out)

@app.post("/debug/echo")
async def debug_echo(req: Request):
    try:
        payload = await req.json()
    except Exception:
        payload = None
    info = {
        "method": req.method,
        "url": str(req.url),
        "client": getattr(req, 'client', None) and getattr(req.client, 'host', None),
        "content_type": req.headers.get("content-type"),
        "origin": req.headers.get("origin"),
        "payload": payload,
    }
    return JSONResponse({"ok": True, "info": info})


# Perplexity debug endpoint removed
