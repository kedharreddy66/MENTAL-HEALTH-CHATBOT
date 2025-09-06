# src/mh_core/content_loader.py
from pathlib import Path
import json

# This file loads your editable content pack at: content/en_aus_pack.json
# Project layout assumed:
#   mh-chatbot/
#     ├─ content/en_aus_pack.json
#     └─ src/mh_core/content_loader.py

# Resolve path to the project root, then to content/en_aus_pack.json
CONTENT_PATH = Path(__file__).resolve().parents[2] / "content" / "en_aus_pack.json"

def _load_pack():
    if not CONTENT_PATH.exists():
        raise FileNotFoundError(
            f"Content pack not found at {CONTENT_PATH}. "
            "Make sure the file exists and the path is correct."
        )
    with open(CONTENT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

PACK = _load_pack()
STRINGS = PACK.get("strings", {})
EXAMPLES = PACK.get("examples", {})
