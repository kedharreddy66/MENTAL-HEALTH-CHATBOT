import re

_REPLACEMENTS = [
    (r"\bhello\b", "hey"),
    (r"\bhi\b", "hey"),
    (r"\bdiscuss\b", "yarn"),
    (r"\btalk\b", "yarn"),
    (r"\bconversation\b", "yarn"),
    (r"\bexcellent\b", "deadly"),
    (r"\bgreat\b", "deadly"),
    (r"\bfamily\b", "mob"),
    (r"\bcommunity\b", "mob"),
    (r"\bland\b", "Country"),
    (r"\b(place|homeland)\b", "Country"),
    (r"\bI am\b", "I’m"),
    (r"\byou are\b", "you’re"),
]

_FORMAL_PATTERNS = [
    r"\bI am an AI\b",
    r"\bAs an AI\b",
    r"\bI do not provide medical advice\b",
    r"\bI cannot diagnose\b",
    r"\bI am not a substitute for\b",
]

def _apply_replacements(text: str) -> str:
    out = text
    for pat, rep in _REPLACEMENTS:
        out = re.sub(pat, rep, out, flags=re.IGNORECASE)
    return out

def _strip_formal_disclaimers(text: str) -> str:
    out = text
    for pat in _FORMAL_PATTERNS:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out

def _shorten(text: str, max_sentences: int = 4) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) > max_sentences:
        parts = parts[:max_sentences]
    return " ".join(parts)

def _tidy_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def aboriginal_english_filter(text: str, crisis: bool = False) -> str:
    if not text:
        return text
    out = text
    if crisis:
        out = _strip_formal_disclaimers(out)
        out = _tidy_whitespace(out)
        out = _shorten(out, max_sentences=2)
        return out
    out = _apply_replacements(out)
    out = _strip_formal_disclaimers(out)
    out = _tidy_whitespace(out)
    out = _shorten(out, max_sentences=4)
    return out
