# src/mh_core/safety.py
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import re, json, pathlib, datetime as dt

# ---------- paths
ROOT = pathlib.Path(__file__).parent.parent
CONTENT_DIR = ROOT / "content"
SAFE_CONTACTS_PATH = CONTENT_DIR / "crisis_contacts_au.json"
LOCAL_PATTERNS_PATH = CONTENT_DIR / "crisis_patterns.local.json"

# ---------- built-in patterns (case-insensitive)
# These cover common spacing/wording variants and slang.
CRISIS_BUILTINS: List[str] = [
    r"\bkill\s*my\s*self\b",
    r"\bkill\s*myself\b",
    r"\bi\s*(?:want|wanna|feel like)\s*(?:to\s*)?kill\s*my\s*self\b",
    r"\bi\s*(?:want|wanna|feel like)\s*(?:to\s*)?kill\s*myself\b",
    r"\bkill\s*me\b",
    r"\btake\s*my\s*life\b",
    r"\bend(?:ing)?\s*(?:it|my\s*life)\b",
    r"\bi\s*(?:want|wanna|feel like)\s*(?:to\s*)?(?:die|not\s*be\s*alive)\b",
    r"\bi\s*do(?:n'?| no)t\s*want\s*to\s*live\b",
    r"\bself[-\s]*harm\b",
    r"\bcut(?:ting)?\s*myself\b",
    r"\bkys\b",
]

# ---------- results
@dataclass
class SafetyResult:
    level: str                # 'none' | 'monitor' | 'crisis'
    trigger: Optional[str]    # matched phrase
    contacts: Optional[Dict[str, Any]] = None

# ---------- helpers
def _load_local_patterns() -> List[str]:
    """Optionally extend patterns with local JSON (list of regex strings)."""
    try:
        data = json.loads(LOCAL_PATTERNS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [p for p in data if isinstance(p, str)]
    except Exception:
        pass
    return []

def _all_patterns() -> List[re.Pattern]:
    patterns = list(CRISIS_BUILTINS) + _load_local_patterns()
    return [re.compile(p, flags=re.IGNORECASE) for p in patterns]

def load_contacts() -> Dict[str, Any]:
    try:
        return json.loads(SAFE_CONTACTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        # Fallback AU services
        return {
            "emergency": "000",
            "lifeline": "13 11 14",
            "kids_helpline": "1800 551 800",
            "suicide_callback": "1300 659 467",
            "mensline": "1300 789 978",
            "beyond_blue": "1300 22 4636",
            "headspace": "1800 650 890",
            "qlife": "1800 184 527",
        }

# ---------- main API used by the gateway
def assess_message(text: str) -> SafetyResult:
    if not text:
        return SafetyResult(level="none", trigger=None)

    # Crisis check
    for cre in _all_patterns():
        m = cre.search(text)
        if m:
            return SafetyResult(level="crisis", trigger=m.group(0), contacts=load_contacts())

    # Passive-ideation / monitoring tier (generic)
    if re.search(r"\b(no\s*reason\s*to\s*live|don.?t\s*care\s*if\s*i\s*die|i\s*can.?t\s*go\s*on)\b",
                 text, flags=re.IGNORECASE):
        return SafetyResult(level="monitor", trigger="passive_ideation")

    return SafetyResult(level="none", trigger=None)


# Override crisis text with plain English, no slang or contractions
def crisis_opening(name: Optional[str], contacts: Dict[str, Any]) -> str:  # type: ignore[override]
    who = name or "there"; _ = who
    dt.datetime.now()
    return (
        "I am really sorry you are feeling this way. I hear you.\n\n"
        "Right now, your safety comes first. Are you in immediate danger, or have you taken anything just now?\n\n"
        f"If you are in danger, please call **000** or go to the nearest emergency department.\n"
        f"You can also ring **Lifeline {contacts.get('lifeline','13 11 14')}** or **Suicide Call Back Service {contacts.get('suicide_callback','1300 659 467')}**. "
        f"If you are under 25, **Kids Helpline {contacts.get('kids_helpline','1800 551 800')}** can help.\n\n"
        "Can we talk a little to keep you safe right now? Where are you? Is there someone nearbyâ€”family or a trusted personâ€”who can sit with you?"
    )


def crisis_followups(contacts: Dict[str, Any]) -> Dict[str, str]:  # type: ignore[override]
    return {
        "means": "Do you have anything around you right now that you could use to hurt yourself? If yes, can we put it away or move to a safer place while we talk?",
        "plan": "Have you been thinking about how you might hurt yourself (a plan), or is it more like strong, painful thoughts?",
        "support": "Who are your strong peopleâ€”family, Elders, friendsâ€”who help keep you steady? Could one of them be with you now?",
        "commit": "Let us make a small plan for tonight. One step could be calling Lifeline together, or sitting with a family member. Which feels okay to try first?",
        "resources": "When you are not in immediate danger, I can share Stay Strong resources and we can set a small goal that fits your way of doing things.",
    }




