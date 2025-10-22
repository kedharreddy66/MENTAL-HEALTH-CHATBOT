from typing import Tuple
import re


POS_WORDS = {
    "good", "great", "nice", "love", "like", "happy", "calm", "proud",
    "relief", "relieved", "strong", "better", "glad", "hope", "hopeful",
    "okay", "ok", "alright", "fine",
}

NEG_WORDS = {
    "bad", "worse", "worst", "sad", "down", "low", "flat", "angry", "mad",
    "upset", "anxious", "anxiety", "panic", "stressed", "stress", "tired",
    "exhausted", "lonely", "hurt", "scared", "fear", "worried", "worry",
    "depressed", "depress", "overwhelmed", "hate", "useless", "broken",
}

NEGATORS = {"not", "no", "never", "hardly", "barely", "isn't", "isnt", "don't", "dont", "can't", "cant"}
BOOSTERS = {"very", "really", "so", "too", "pretty", "quite", "super"}
DEBOOSTERS = {"slightly", "a bit", "somewhat", "kinda", "kind of", "sort of"}


def _tokenize(text: str):
    text = (text or "").lower()
    # keep simple words and contractions
    return re.findall(r"[a-zA-Z']+", text)


def analyze_sentiment(text: str) -> Tuple[str, float]:
    """
    Lightweight lexicon-based sentiment with negation and booster handling.
    Returns (label, score in [-1.0, 1.0]). Fails safe to ("neutral", 0.0).
    """
    try:
        toks = _tokenize(text)
        if not toks:
            return "neutral", 0.0
        score = 0.0
        window_negate = 0
        window_boost = 1.0
        for i, w in enumerate(toks):
            # windowed negation (flip next 3 sentiment-bearing words)
            if w in NEGATORS:
                window_negate = 3
                continue
            # boosters / deboosters influence magnitude of next 2 hits
            if w in BOOSTERS:
                window_boost = max(window_boost, 1.5)
                continue
            if w in DEBOOSTERS:
                window_boost = min(window_boost, 0.7)
                continue

            val = 0.0
            if w in POS_WORDS:
                val = 1.0
            elif w in NEG_WORDS:
                val = -1.0

            if val != 0.0:
                if window_negate > 0:
                    val = -val
                    window_negate -= 1
                val *= window_boost
                # decay booster after use
                window_boost = 1.0
                score += val

        # normalize by rough scale to [-1, 1]
        norm = max(-1.0, min(1.0, score / 4.0))
        if norm > 0.2:
            return "positive", norm
        if norm < -0.2:
            return "negative", norm
        return "neutral", norm
    except Exception:
        return "neutral", 0.0

