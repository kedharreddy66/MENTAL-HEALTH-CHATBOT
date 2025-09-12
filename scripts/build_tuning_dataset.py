import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"


def load_jsonl(path: Path):
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except Exception:
            pass
    return items


def topic_to_prompt(topic: str, text: str) -> str:
    t = (topic or "").lower()
    if t in ("strengths",):
        return "What helps me feel strong?"
    if "study" in t:
        return "I feel stressed about study. Any ideas?"
    if "sleep" in t:
        return "I am having trouble with sleep. What could help?"
    if "mental" in t:
        return "Can you explain mental wellbeing in simple words?"
    if "alcohol" in t or "cannabis" in t or "substance" in t:
        return "I sometimes use alcohol or cannabis. How can I make safer choices?"
    if "goal" in t:
        return "Can you help me pick a small, doable goal?"
    if "support" in t:
        return "Who could support me with my plan?"
    if "check" in t:
        return "How can I check in with myself and my plan?"
    if "identity" in t or "culture" in t:
        return "How can culture and Country help me feel strong?"
    if "anxiety" in t or "worry" in t:
        return "I feel anxious. What could I try right now?"
    if "racism" in t:
        return "If racism happens, what can I do to look after myself?"
    if "crisis" in t:
        return "If someone is in crisis, what is a safe next step?"
    return "Can you share a simple idea that could help?"


def main():
    out_dir = ROOT / "tuning"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "dataset.jsonl"

    basics = load_jsonl(CONTENT / "knowledge" / "aimhiy_basics.jsonl")
    snippets = load_jsonl(CONTENT / "knowledge" / "stay_strong_snippets.jsonl")
    idx_meta = json.loads((CONTENT / "index_meta.json").read_text(encoding="utf-8"))

    # Style guide to embed as system for every example
    sgp = (CONTENT / "style_guide_local.json")
    style_append = ""
    try:
        style_append = json.loads(sgp.read_text(encoding="utf-8")).get("append", "")
    except Exception:
        pass

    def make_record(user: str, assistant: str):
        return {
            "messages": [
                {"role": "system", "content": style_append},
                {"role": "user", "content": user},
                {"role": "assistant", "content": assistant},
            ]
        }

    records = []

    for item in basics:
        user = topic_to_prompt(item.get("topic", ""), item.get("text", ""))
        assistant = item.get("text", "")
        if user and assistant:
            records.append(make_record(user, assistant))

    # Use index_meta texts as additional assistant targets
    for item in idx_meta:
        user = topic_to_prompt(item.get("topic", ""), item.get("text", ""))
        assistant = item.get("text", "")
        if user and assistant:
            records.append(make_record(user, assistant))

    # Add a few direct “closing/check-in” style prompts from snippets
    for s in snippets:
        topic = s.get("topic", "")
        text = s.get("text", "")
        if not text:
            continue
        if topic in {"closing", "check_in", "support", "goals", "sleep", "anxiety"}:
            user = topic_to_prompt(topic, text)
            records.append(make_record(user, text))

    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} examples -> {out_path}")


if __name__ == "__main__":
    main()

