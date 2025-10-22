import os
import hmac
import json
import base64
import hashlib
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import smtplib
from email.message import EmailMessage


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
USERS_PATH = DATA_DIR / "users.json"
STATES_DIR = DATA_DIR / "states"
PENDING_PATH = DATA_DIR / "pending.json"
OUTBOX_DIR = DATA_DIR / "outbox"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATES_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _write_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _hash_password(password: str, salt: Optional[bytes] = None) -> Dict[str, str]:
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return {
        "salt": _b64url(salt),
        "hash": _b64url(dk),
        "algo": "pbkdf2_sha256",
        "iters": 100_000,
    }


def _verify_password(password: str, rec: Dict[str, Any]) -> bool:
    try:
        salt = _b64url_decode(rec.get("salt", ""))
        expected = _b64url_decode(rec.get("hash", ""))
        iters = int(rec.get("iters", 100_000))
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def _users() -> Dict[str, Any]:
    _ensure_dirs()
    return _load_json(USERS_PATH, {"by_username": {}, "by_id": {}})


def _save_users(data: Dict[str, Any]):
    _write_json(USERS_PATH, data)


 


def create_user(username: str, password: Optional[str], email: Optional[str] = None, email_verified: bool = False) -> Dict[str, Any]:
    username = (username or "").strip().lower()
    if not username:
        raise ValueError("Invalid username")
    if password is not None and len(password or "") < 6:
        raise ValueError("Password too short (min 6)")
    data = _users()
    if username in data["by_username"]:
        raise ValueError("Username already exists")
    uid = str(uuid.uuid4())
    pwd = _hash_password(password) if password else None
    rec = {
        "id": uid,
        "username": username,
        "email": (email or '').lower() or None,
        "email_verified": bool(email_verified),
        "password": pwd,
        "created_at": int(time.time()),
    }
    data["by_username"][username] = uid
    data["by_id"][uid] = rec
    _save_users(data)
    return {"id": uid, "username": username, "email": rec["email"]}


def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    username = (username or "").strip().lower()
    data = _users()
    uid = data["by_username"].get(username)
    if not uid:
        return None
    rec = data["by_id"].get(uid)
    if rec and _verify_password(password or "", rec.get("password", {})):
        return {"id": uid, "username": username, "email": rec.get("email")}
    return None

def authenticate_by_email(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate using an email + password pair.
    Looks up the user by email and verifies the stored password hash.
    Returns minimal user dict on success, else None.
    """
    email = (email or "").strip().lower()
    data = _users()
    for uid, rec in data.get("by_id", {}).items():
        if (rec.get("email") or "").lower() == email:
            if rec.get("password") and _verify_password(password or "", rec.get("password", {})):
                return {"id": uid, "username": rec.get("username"), "email": rec.get("email")}
            return None
    return None


def get_user(uid: str) -> Optional[Dict[str, Any]]:
    data = _users()
    rec = data["by_id"].get(uid)
    if not rec:
        return None
    return {"id": rec["id"], "username": rec["username"], "email": rec.get("email")}


def auth_secret() -> bytes:
    return (os.getenv("AUTH_SECRET") or "dev-secret-change-me").encode("utf-8")


def create_token(user_id: str, username: str, ttl_hours: int = 72) -> str:
    now = int(time.time())
    payload = {"sub": user_id, "usr": username, "iat": now, "exp": now + ttl_hours * 3600}
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(auth_secret(), msg=f"{h}.{p}".encode("utf-8"), digestmod=hashlib.sha256).digest()
    s = _b64url(sig)
    return f"{h}.{p}.{s}"


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h, p, s = parts
        sig = hmac.new(auth_secret(), msg=f"{h}.{p}".encode("utf-8"), digestmod=hashlib.sha256).digest()
        if not hmac.compare_digest(sig, _b64url_decode(s)):
            return None
        payload = json.loads(_b64url_decode(p).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


# OTP and email helpers
def _pending() -> Dict[str, Any]:
    _ensure_dirs()
    return _load_json(PENDING_PATH, {"signup": {}, "login": {}, "oauth": {}})


def _save_pending(data: Dict[str, Any]):
    _write_json(PENDING_PATH, data)


def _gen_code() -> str:
    return str(int.from_bytes(os.urandom(3), 'big') % 1_000_000).zfill(6)


def _hash_code(code: str) -> str:
    # Bind to AUTH_SECRET for at-rest obscurity
    return _b64url(hashlib.sha256((code + "|" + auth_secret().decode("utf-8", errors="ignore")).encode("utf-8")).digest())


def _smtp_settings() -> Optional[Tuple[str, int, Optional[str], Optional[str], Optional[str]]]:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT") or 587)
    user = os.getenv("SMTP_USER")
    pwd = os.getenv("SMTP_PASS")
    sender = os.getenv("SMTP_FROM") or (user if user else None)
    if not host or not sender:
        return None
    return host, port, user, pwd, sender


def _send_email(to_email: str, subject: str, body: str) -> bool:
    """Send via SMTP if configured; else write to outbox and return True.
    In dev, OTP will be written to files under data/outbox.
    """
    cfg = _smtp_settings()
    if not cfg:
        try:
            OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
            fname = f"{int(time.time())}_{to_email.replace('@','_').replace('.','_')}.txt"
            (OUTBOX_DIR / fname).write_text(f"To: {to_email}\nSubject: {subject}\n\n{body}", encoding="utf-8")
            if os.getenv("DEBUG_OTP"):
                print(f"[OTP] DEV OUTBOX -> {to_email}: {body}")
            return True
        except Exception:
            return False
    host, port, user, pwd, sender = cfg
    try:
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.starttls()
            if user and pwd:
                s.login(user, pwd)
            s.send_message(msg)
        if os.getenv("DEBUG_OTP"):
            print(f"[OTP] SMTP SENT -> {to_email}: {body}")
        return True
    except Exception:
        return False


def _read_dev_latest_otp(email: str) -> Optional[str]:
    """Best-effort: read most recent OTP from outbox files for given email (dev only)."""
    try:
        if not OUTBOX_DIR.exists():
            return None
        candidates = sorted(OUTBOX_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        for p in candidates:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            if f"To: {email}" in txt:
                # Find 6-digit sequences
                import re
                m = re.search(r"\b(\d{6})\b", txt)
                if m:
                    return m.group(1)
        return None
    except Exception:
        return None


def request_signup(email: str, username: str, client_ip: Optional[str] = None) -> Dict[str, Any]:
    now = int(time.time())
    email = (email or '').lower().strip()
    username = (username or '').lower().strip()
    if not email or not username:
        raise ValueError("Email and username required")
    data = _pending()
    # throttle by IP (simple token bucket)
    if client_ip:
        ipm = data.setdefault("ip", {})
        iprec = ipm.get(client_ip) or {"count": 0, "ts": now}
        # reset window every 10 minutes
        if now - int(iprec.get("ts", 0)) > 600:
            iprec = {"count": 0, "ts": now}
        if int(iprec.get("count", 0)) >= 10:
            raise ValueError("Too many requests from your network. Try later.")
        iprec["count"] = int(iprec.get("count", 0)) + 1
        iprec["ts"] = now
        ipm[client_ip] = iprec
    # throttle by email cooldown
    ps = data.setdefault("signup", {})
    p = ps.get(email) or {}
    last = int(p.get("ts", 0))
    if now - last < 30:
        raise ValueError("Please wait before requesting another code")
    code = _gen_code()
    # OTP expires in 5 minutes
    ps[email] = {"email": email, "username": username, "code_hash": _hash_code(code), "ts": now, "exp": now + 5*60}
    _save_pending(data)
    subject = "MH Chatbot: Verify your email (5‑min code)"
    body = (
        f"Your verification code is: {code}\n"
        f"This code expires in 5 minutes.\n\n"
        f"If you didn’t request this, you can ignore this email.\n"
        f"For your security, don’t share this code with anyone.\n"
    )
    sent = _send_email(email, subject, body)
    if not sent:
        raise ValueError("Could not send email (check SMTP settings)")
    return {"ok": True, "cooldown": 30, "expires_in": 300}


def verify_signup(email: str, username: str, code: str, password: Optional[str] = None) -> Dict[str, Any]:
    now = int(time.time())
    email = (email or '').lower().strip()
    username = (username or '').lower().strip()
    code = (code or '').strip()
    data = _pending()
    ps = data.setdefault("signup", {})
    rec = ps.get(email)
    if not rec or rec.get("username") != username:
        raise ValueError("No signup pending for this email")
    if now > int(rec.get("exp", 0)):
        raise ValueError("Code expired. Request a new one.")
    if _hash_code(code) != rec.get("code_hash"):
        raise ValueError("Invalid code")
    # Create user with optional password (allows password sign-in later)
    pwd = None
    if password is not None:
        if len(password) < 6:
            raise ValueError("Password too short (min 6)")
        pwd = password
    user = create_user(username=username, password=pwd, email=email, email_verified=True)
    # cleanup
    ps.pop(email, None)
    _save_pending(data)
    return user


def request_login(email: str, client_ip: Optional[str] = None) -> Dict[str, Any]:
    now = int(time.time())
    email = (email or '').lower().strip()
    if not email:
        raise ValueError("Email required")
    data = _pending()
    # throttle by IP
    if client_ip:
        ipm = data.setdefault("ip", {})
        iprec = ipm.get(client_ip) or {"count": 0, "ts": now}
        if now - int(iprec.get("ts", 0)) > 600:
            iprec = {"count": 0, "ts": now}
        if int(iprec.get("count", 0)) >= 10:
            raise ValueError("Too many requests from your network. Try later.")
        iprec["count"] = int(iprec.get("count", 0)) + 1
        iprec["ts"] = now
        ipm[client_ip] = iprec
    pl = data.setdefault("login", {})
    p = pl.get(email) or {}
    last = int(p.get("ts", 0))
    if now - last < 30:
        raise ValueError("Please wait before requesting another code")
    code = _gen_code()
    # OTP expires in 5 minutes
    pl[email] = {"email": email, "code_hash": _hash_code(code), "ts": now, "exp": now + 5*60}
    _save_pending(data)
    subject = "MH Chatbot: Sign in code (5‑min OTP)"
    body = (
        f"Your sign in code is: {code}\n"
        f"This code expires in 5 minutes.\n\n"
        f"If you didn’t request this, you can ignore this email.\n"
        f"For your security, don’t share this code with anyone.\n"
    )
    sent = _send_email(email, subject, body)
    if not sent:
        raise ValueError("Could not send email (check SMTP settings)")
    return {"ok": True, "cooldown": 30, "expires_in": 300}


 


def verify_login(email: str, code: str) -> Optional[Dict[str, Any]]:
    now = int(time.time())
    email = (email or '').lower().strip()
    code = (code or '').strip()
    data = _pending()
    pl = data.setdefault("login", {})
    rec = pl.get(email)
    if not rec:
        return None
    if now > int(rec.get("exp", 0)):
        raise ValueError("Code expired. Request a new one.")
    if _hash_code(code) != rec.get("code_hash"):
        return None
    # find user by email
    users = _users()
    for u in users["by_id"].values():
        if (u.get("email") or '').lower() == email:
            pl.pop(email, None)
            _save_pending(data)
            return {"id": u["id"], "username": u["username"], "email": u.get("email")}
    return None


def otp_status(email: str) -> Dict[str, Any]:
    """Return cooldown and expiry hints for UX timers."""
    now = int(time.time())
    email = (email or '').lower().strip()
    data = _pending()
    out: Dict[str, Any] = {"signup": None, "login": None}
    rec = data.get("signup", {}).get(email)
    if rec:
        cd = max(0, 30 - (now - int(rec.get("ts", 0))))
        ex = max(0, int(rec.get("exp", 0)) - now)
        out["signup"] = {"cooldown": cd, "expires_in": ex}
    rec2 = data.get("login", {}).get(email)
    if rec2:
        cd2 = max(0, 30 - (now - int(rec2.get("ts", 0))))
        ex2 = max(0, int(rec2.get("exp", 0)) - now)
        out["login"] = {"cooldown": cd2, "expires_in": ex2}
    return out


# OAuth helpers (Google/Apple)
def _suggest_username(email: str, existing: Dict[str, Any]) -> str:
    base = (email.split('@',1)[0] or 'user').lower()
    uname = base
    taken = set(existing.get("by_username", {}).keys())
    i = 1
    while uname in taken:
        i += 1
        uname = f"{base}{i}"
    return uname


def upsert_user_by_email(email: str) -> Dict[str, Any]:
    email = (email or '').lower().strip()
    if not email:
        raise ValueError("Email required")
    data = _users()
    # Try find existing by email
    for uid, rec in data["by_id"].items():
        if (rec.get("email") or '').lower() == email:
            return {"id": rec["id"], "username": rec["username"], "email": rec.get("email")}
    # Create new
    uname = _suggest_username(email, data)
    user = create_user(username=uname, password=None, email=email, email_verified=True)
    return user


def oauth_new_state(provider: str) -> str:
    st = base64.urlsafe_b64encode(os.urandom(18)).rstrip(b"=").decode("ascii")
    data = _pending()
    oauth = data.setdefault("oauth", {})
    now = int(time.time())
    oauth[st] = {"provider": provider, "ts": now, "exp": now + 600}
    _save_pending(data)
    return st


def oauth_consume_state(state: str, provider: str) -> bool:
    data = _pending()
    oauth = data.setdefault("oauth", {})
    rec = oauth.get(state)
    ok = bool(rec and rec.get("provider") == provider and int(rec.get("exp",0)) >= int(time.time()))
    if rec:
        oauth.pop(state, None)
        _save_pending(data)
    return ok


def read_state(user_id: str) -> Optional[Dict[str, Any]]:
    _ensure_dirs()
    path = STATES_DIR / f"{user_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_state(user_id: str, state: Dict[str, Any]):
    _ensure_dirs()
    path = STATES_DIR / f"{user_id}.json"
    _write_json(path, state)


def clear_state(user_id: str):
    try:
        path = STATES_DIR / f"{user_id}.json"
        if path.exists():
            path.unlink(missing_ok=True)  # type: ignore
    except Exception:
        pass
