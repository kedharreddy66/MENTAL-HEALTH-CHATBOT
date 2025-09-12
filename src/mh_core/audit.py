# src/mh_core/audit.py
"""
Rule-based conversation auditor for the MH chatbot.

Usage:
  POST /audit with:
    {
      "messages": [
        {"role":"user","text":"..."},
        {"role":"bot","text":"..."},
        ...
      ]
    }

Returns a report with issues, suggestions, and a simple score.
This does not call an LLM and contains no explicit crisis phrases.
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
import re

# Import ONLY the public function; no circular deps
from .safety import assess_message

# ------------ helpers

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def _is_worry_signal(text: str) -> bool:
    t = _norm(text)
    WORRY_WORDS = [
        "stress", "stressed", "anxious", "anxiety", "panic", "sad", "depress", "low",
        "angry", "anger", "overwhelm", "worried", "worry", "scared", "fear",
        "tired", "exhausted", "burnt out", "burned out", "lonely",
        "sleep", "insomnia", "problem", "issue", "help", "advice",
        "exam", "assignment", "money", "bills", "rent", "job", "work"
    ]
    return any(w in t for w in WORRY_WORDS)

def _looks_like_people_answer(text: str) -> bool:
    t = _norm(text)
    PEOPLE = [
        "family","elder","elders","friend","friends","mate","mates","mum","mom","dad",
        "mother","father","nan","pop","grandma","grandpa","aunty","uncle","cousin","cousins",
        "brother","sister","siblings","partner","boyfriend","girlfriend","husband","wife",
        "kids","children","child","son","daughter","mob","community","coach","teacher",
        "counsellor","counselor","worker"
    ]
    return any(p in t for p in PEOPLE)

def _step_from_bot_text(text: str) -> int:
    """Heuristic to guess which Stay Strong step a bot message belongs to."""
    t = _norm(text)
    if "who helps keep you steady" in t or ("family" in t and "elders" in t and "friends" in t):
        return 1
    if "what are the things that keep you strong" in t or "keep you strong" in t:
        return 2
    if "when you’re ready" in t and "worries" in t:
        return 3
    if "let’s pick one small change" in t or "one small thing" in t:
        return 4
    return 0

@dataclass
class Issue:
    type: str        # 'design', 'cultural', 'technical', 'safety', 'accessibility'
    severity: str    # 'low' | 'medium' | 'high' | 'critical'
    message: str
    suggestion: str
    example: str = ""

    def to_dict(self) -> Dict:
        d = {"type": self.type, "severity": self.severity, "message": self.message, "suggestion": self.suggestion}
        if self.example:
            d["example"] = self.example
        return d

# ------------ main

def audit_conversation(messages: List[Dict[str, str]]) -> Dict:
    """
    messages: [{"role": "user"|"bot", "text": "..."}]
    """
    issues: List[Issue] = []
    if not isinstance(messages, list) or not all(isinstance(m, dict) and "role" in m and "text" in m for m in messages):
        return {"ok": False, "error": "messages must be a list of {role, text}"}

    # 1) Crisis/safety signal scanning (generic — uses your local patterns)
    for m in messages:
        if m.get("role") == "user":
            sr = assess_message(m.get("text", ""))
            if sr.level == "crisis":
                issues.append(Issue(
                    "safety", "critical",
                    "Potential crisis signal detected in a user message.",
                    "Ensure the bot enters crisis mode: ask about immediate danger, encourage contacting 000/Lifeline, invite a trusted person to sit with them, and keep messages short and calm.",
                    example=m.get("text", "")
                ))
            elif sr.level == "monitor":
                issues.append(Issue(
                    "safety", "medium",
                    "Passive ideation signal detected (monitoring tier).",
                    "Acknowledge feelings and ask gentle follow-ups; offer strengths-based resources and helpline info if appropriate.",
                    example=m.get("text", "")
                ))

    # 2) Early-turn branching: did the user share a worry but the bot pushed straight to Step 1 without acknowledgement?
    # We look at the first user+bot pair.
    first_user = next((m for m in messages if m.get("role") == "user"), None)
    first_bot = next((m for m in messages if m.get("role") == "bot"), None)
    if first_user and first_bot:
        if _is_worry_signal(first_user.get("text","")):
            bot_text = _norm(first_bot.get("text", ""))
            if "thanks for" not in bot_text and "i hear you" not in bot_text and "i’m here" not in bot_text:
                issues.append(Issue(
                    "design", "medium",
                    "User shared a worry in the first turn but the bot didn’t acknowledge before guiding to the model flow.",
                    "Begin with a short reflection (e.g., “I hear you”), then guide to supports/strengths or worries.",
                    example=f'user: {first_user.get("text","")}\nbot: {first_bot.get("text","")[:140]}…'
                ))
            if _step_from_bot_text(first_bot.get("text","")) == 1:
                issues.append(Issue(
                    "design", "low",
                    "Bot moved to Step 1 (support people) right after a worry. This can feel dismissive.",
                    "Acknowledge the worry first and, if urgent, branch to the worries step earlier.",
                    example=first_bot.get("text","")[:160]
                ))

    # 3) Repetition: identical bot lines in a row
    last_bot = None
    rep_count = 0
    for m in messages:
        if m.get("role") == "bot":
            txt = _norm(m.get("text",""))
            if txt and txt == last_bot:
                rep_count += 1
            else:
                last_bot = txt
                rep_count = 0
            if rep_count >= 1:
                issues.append(Issue(
                    "design", "medium",
                    "Bot repeated the same message multiple times.",
                    "Track conversation state and vary phrasing; avoid sending the same prompt twice.",
                    example=m.get("text","")[:160]
                ))

    # 4) Accessibility: very long bot messages (split into shorter chunks/bullets)
    for m in messages:
        if m.get("role") == "bot":
            text = m.get("text","")
            if len(text) > 420:
                issues.append(Issue(
                    "accessibility", "low",
                    "Bot message is quite long.",
                    "Split into shorter messages with clear bullets; allow the user to respond in between.",
                    example=text[:160] + ("…" if len(text) > 160 else "")
                ))

    # 5) Cultural framing: check if early bot messages mention family/Elders/friends or Country at least once
    early_bots = [m.get("text","") for m in messages if m.get("role") == "bot"][:3]
    joined = " ".join(early_bots).lower()
    if not (("elders" in joined and "family" in joined) or "country" in joined or "mob" in joined):
        issues.append(Issue(
            "cultural", "low",
            "Early conversation doesn’t reference strong people or Country.",
            "Include a gentle prompt about family/Elders/friends and Country (as appropriate) to align with Stay Strong.",
        ))

    # 6) Flow order: detect big jumps or missing worries step
    steps = [_step_from_bot_text(m.get("text","")) for m in messages if m.get("role") == "bot"]
    if steps:
        if 4 in steps and 3 not in steps:
            issues.append(Issue(
                "design", "low",
                "Goal-setting (Step 4) occurred without an explicit worries step.",
                "Make sure the bot invites the person to name a worry before moving to goal-setting, unless they’ve already done so.",
            ))

    # Compute a simple score (start at 100, subtract per issue by severity)
    penalties = {"low": 2, "medium": 6, "high": 12, "critical": 25}
    score = 100
    for it in issues:
        score -= penalties.get(it.severity, 2)
    score = max(0, score)

    return {"ok": True, "score": score, "issues": [i.to_dict() for i in issues]}
