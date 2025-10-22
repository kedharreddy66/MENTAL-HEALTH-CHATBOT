from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_if_present() -> None:
    """Load KEY=VALUE lines from a project-root .env file if present.
    - Does not override already-set environment variables.
    - Ignores blank lines and lines starting with '#'.
    """
    try:
        root = Path(__file__).resolve().parents[2]
        env_path = root / ".env"
        if not env_path.exists():
            return
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and (key not in os.environ):
                os.environ[key] = val
    except Exception:
        # Non-fatal; silently skip if anything goes wrong.
        pass

