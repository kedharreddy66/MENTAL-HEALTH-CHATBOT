from __future__ import annotations
from typing import List, Tuple
from pathlib import Path
import json

_LEX_PATH = Path(__file__).resolve().parents[2] / "content" / "cultural_lexicon.json"
_TERMS: List[Tuple[str, str]] = []

def _load_terms() -> List[Tuple[str, str]]:
    global _TERMS
    if _TERMS:
        return _TERMS
    try:
        data = json.loads(_LEX_PATH.read_text(encoding="utf-8"))
        pairs = []
        for t in data.get("terms", []):
            p = t.get("phrase"); m = t.get("meaning")
            if isinstance(p, str) and isinstance(m, str) and p:
                pairs.append((p, m))
        # sort by phrase length desc so multi-word terms replace first
        pairs.sort(key=lambda x: len(x[0]), reverse=True)
        _TERMS = pairs
    except Exception:
        _TERMS = []
    return _TERMS


def normalize_for_retrieval(text: str) -> Tuple[str, List[str]]:
    """
    Returns a (normalized_text, notes) tuple.
    - normalized_text: original text with Aboriginal English terms replaced by plain-English meanings
      for retrieval purposes (case-insensitive, basic word-boundary matching where possible).
    - notes: short bullet strings like "yarn -> talk or have a conversation" to help the model interpret terms.
    """
    s = text or ""
    if not s:
        return s, []
    terms = _load_terms()
    low = s.lower()
    notes: List[str] = []
    out = s
    # simple case-insensitive replace; handle word-ish boundaries for single words
    for phrase, meaning in terms:
        pl = phrase.lower()
        if pl in low:
            notes.append(f"{phrase} -> {meaning}")
            # naive replace ignoring punctuation; keep it simple and safe
            out = out.replace(phrase, meaning)
            out = out.replace(phrase.lower(), meaning)
            out = out.replace(phrase.title(), meaning)
    return out, notes

