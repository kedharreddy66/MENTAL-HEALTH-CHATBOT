"""
Crisis detection and support helpers.

Behaviour:
- If DEV_BYPASS_CRISIS=true, detection is disabled and functions no-op.
- Otherwise uses regex patterns to detect crisis terms and can format
  helpline numbers from content/crisis_contacts_au.json.
"""
import os
import re
import sys
import json
from datetime import datetime
from pathlib import Path

# Default to enabled in production; can opt-out via env
_DEV_BYPASS = os.getenv("DEV_BYPASS_CRISIS", "false").lower() in ("1", "true", "yes")

_CRISIS_TERMS = [
    r"\bsuicide\b", r"\bsuicidal\b", r"\bend it\b", r"\bend my life\b",
    r"\bkill myself\b", r"\bkill me\b", r"\bi want to die\b", r"\bi wanna die\b",
    r"\bi want to end it\b", r"\bending it\b", r"\bi can'?t go on\b",
    r"\bno reason to live\b", r"\bself[- ]?harm\b", r"\bhurt myself\b",
    r"\bnot safe\b", r"\bcan'?t stay safe\b", r"\bgive up\b"
]
_CRISIS_RE = re.compile("|".join(_CRISIS_TERMS), re.IGNORECASE)

def contains_crisis_signal(text: str) -> bool:
    """Return False in dev mode; otherwise regex-detect common crisis terms."""
    if _DEV_BYPASS:
        return False
    if not text:
        return False
    match = _CRISIS_RE.search(text)
    if match:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[CRISIS DETECTED] {timestamp} | User said: \"{text}\"", file=sys.stderr)
        return True
    return False

def support_lines() -> list[str]:
    """Return helpline lines for display. Empty if bypassing or file missing."""
    if _DEV_BYPASS:
        return []
    try:
        root = Path(__file__).resolve().parents[2]
        path = root / "content" / "crisis_contacts_au.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        # Keep a friendly, short list
        mapping = {
            "Emergency": data.get("emergency"),
            "Emergency (mobile)": data.get("emergency_mobile"),
            "13YARN": data.get("13yarn"),
            "Lifeline": data.get("lifeline"),
            "Kids Helpline": data.get("kids_helpline"),
            "Suicide Call Back": data.get("suicide_callback"),
            "Beyond Blue": data.get("beyond_blue"),
        }
        lines = []
        for label, num in mapping.items():
            if num:
                lines.append(f"- {label}: {num}")
        return lines
    except Exception:
        return []

def looks_okay_response(text: str) -> bool:
    """Heuristic to detect if user indicates they are okay/safe and not seeking help now."""
    if not text:
        return False
    low = text.strip().lower()
    positive = [
        "i'm okay", "im okay", "i am okay", "i'm ok", "im ok", "i am ok",
        "i'm fine", "im fine", "fine", "okay", "ok",
        "all good", "allgood", "doing good", "good now", "feeling good",
        "better now", "feeling better", "bit better", "im better", "i'm better",
        "sorted", "no worries", "no worry", "no wori",
        "safe now", "i'm safe", "im safe", "i am safe",
        "not now", "not really", "no thanks", "no thank you", "nah", "no",
        "maybe later", "later", "another time", "not needed", "no need",
    ]
    negatives = [
        "not safe", "unsafe", "can't stay safe", "cant stay safe",
        "still struggling", "struggling", "worse", "really bad", "not okay", "not ok",
        "hurt myself", "self-harm", "suicide", "end it", "end my life",
        "want to die", "want to end it", "kill myself", "kill me",
        "need help", "please help",
    ]
    # If positive signals present and no strong negatives, treat as okay
    if any(p in low for p in positive) and not any(n in low for n in negatives):
        return True
    return False
