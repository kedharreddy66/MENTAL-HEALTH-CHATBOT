import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "content" / "scenarios.json"
OUT = ROOT / "tuning" / "dataset.jsonl"

SYS = (
    "Short, plain English. No slang or contractions.\n"
    "Be respectful and strengths-based.\n"
    "Offer up to two small, doable ideas.\n"
    "Do not include phone numbers or links; the app handles helplines.\n"
)


def as_list(x):
    if not x:
        return []
    return x if isinstance(x, list) else [x]


def make_user_intro(s):
    age = s.get("age_group", "").lower()
    ctx = s.get("context", "").strip()
    prob = s.get("problem", "").strip()
    return f"I'm in the {age} age group. {ctx} {prob}"


def make_user_challenge(s):
    challenges = as_list(s.get("challenges"))
    setting = (s.get("setting") or "").strip()
    if challenges:
        ch = ", ".join(challenges[:2])
        return f"At {setting}, I'm dealing with {ch}. Any simple ideas?"
    return f"I'm at {setting}. Any simple ideas to help?"


def make_reply(s):
    supports = as_list(s.get("supports"))
    theme = s.get("theme", "")
    lines = []
    # idea 1: connect to culture / strengths
    if supports:
        lines.append(f"Try one small step with {supports[0].lower()} (even brief).")
    else:
        lines.append("Try one tiny step that feels safe and doable today.")
    # idea 2: gentle next step
    if len(supports) > 1:
        lines.append(f"If you want, explore {supports[1].lower()} or talk with a trusted person.")
    else:
        lines.append("If you want, talk with a trusted person about what helps.")
    tip = "Focus on what already helps you feel strong (family, Elders, Country)."
    return f"Thanks for sharing. {tip} " + " ".join(lines)


def make_identity_check(s):
    return (
        "Thanks for telling me. Two small ideas you could try: "
        "1) Spend a short time with someone who supports you or with a cultural activity. "
        "2) Pick one tiny step for this week and keep it simple."
    )


def make_crisis_first():
    return (
        "I am really glad you told me; getting support matters."
    )


def make_crisis_check():
    return (
        "Would you like to talk about that? I can share some support options if you want."
    )


def make_records(s):
    # Normal records
    recs = []
    intro = make_user_intro(s)
    ch = make_user_challenge(s)
    reply = make_reply(s)
    recs.append({
        "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": intro},
            {"role": "assistant", "content": reply},
        ]
    })
    recs.append({
        "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": ch},
            {"role": "assistant", "content": make_identity_check(s)},
        ]
    })

    # Crisis-specific behaviour for scenario 8 only
    if int(s.get("id", -1)) == 8:
        recs.append({
            "messages": [
                {"role": "system", "content": SYS + " If the user expresses suicide intent, reply with one short, supportive line and stop. No numbers."},
                {"role": "user", "content": "I keep thinking about ending my life."},
                {"role": "assistant", "content": make_crisis_first()},
            ]
        })
        recs.append({
            "messages": [
                {"role": "system", "content": SYS + " After the first crisis line, ask one gentle permission question. No numbers."},
                {"role": "user", "content": "I'm not safe."},
                {"role": "assistant", "content": make_crisis_check()},
            ]
        })

    return recs


def main():
    data = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    scenarios = data.get("scenarios", [])
    OUT.parent.mkdir(exist_ok=True)
    records = []
    for s in scenarios:
        records.extend(make_records(s))

    with OUT.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} examples -> {OUT}")


if __name__ == "__main__":
    main()

