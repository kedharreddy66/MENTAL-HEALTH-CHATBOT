"""
Development crisis stub:
- contains_crisis_signal() always returns False when DEV_BYPASS_CRISIS=true
- SUPPORT_TEXT is empty (no helplines shown)
Re-enable real detection later by unsetting DEV_BYPASS_CRISIS.
"""
import os
import re
import sys
from datetime import datetime

_DEV_BYPASS = os.getenv("DEV_BYPASS_CRISIS", "true").lower() in ("1", "true", "yes")

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

SUPPORT_TEXT = ""  # no helplines in dev mode
