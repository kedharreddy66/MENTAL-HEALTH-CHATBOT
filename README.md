MH Chatbot
=================

A culturally safe, web-based chatbot that supports a four-step “Stay Strong” plan and provides gentle, plain-English support. No login, no database — runs locally with a simple HTML frontend and a FastAPI backend.

Quick Start (No Login, No DB)
-----------------------------

Requirements
- Python 3.11+
- One model provider:
  - Local: Ollama installed and running (recommended), or
  - Cloud: set `GEMINI_API_KEY` to use Gemini

Steps
1) Install: `pip install fastapi uvicorn pydantic numpy`
2) Run the API: `uvicorn src.mh_core.api:app --reload`
3) Open: `http://127.0.0.1:8000/` (redirects to `chat.html`)

Notes
- No authentication or accounts; tokens are not used.
- No database required. The browser carries conversation state.
- Retrieval (optional): run `python scripts/build_index.py` to build a local index for RAG context. The chatbot still works without it.

Repository Structure
--------------------

- `chat.html`          — Single-page frontend interface.
- `src/`
  - `mh_core/`         — Core backend package (FastAPI + helpers)
    - `api.py`         — Endpoints: `/health`, `/reset`, `/chat`, and static `/chat.html`.
    - `ai_gateway.py`  — LLM gateway + system prompt.
    - `rag.py`         — Retrieval helpers (local index).
    - `models.py`      — Pydantic request/response models.
    - `crisis.py`      — Crisis keyword detection and support lines.
    - `culture.py`     — Normalisation + lexicon support.
    - `safety.py`      — Output safety filters (non-crisis).
    - `audit.py`       — Simple trace/audit helpers.
    - `flow.py`        — Conversation step helpers (optional).
    - `content_loader.py` — Utilities for loading content (optional).
- `content/`           — Knowledge base, style guide, indices.
- `scripts/`           — Utilities (index building, CLI, PDF helpers).
- `tuning/`            — Tuning datasets (optional).
- `tests/`             — Unit tests.

Environment (.env)
------------------

Create a `.env` if you want to set provider keys or tweak defaults.

- LLM options
  - `GEMINI_API_KEY` — enable Google Gemini responses (optional)
  - `GEMINI_MODEL` — e.g., `gemini-2.5-flash` (optional)
  - `MODEL_PROVIDER` — set to `gemini` to force Gemini; otherwise auto-selects
  - `OLLAMA_HOST`, `OLLAMA_PORT`, `OLLAMA_MODEL` — configure local Ollama
- No authentication is used; no email/OTP settings are required.

Running
-------

Windows (PowerShell)
- Ensure Python: `python --version`
- Install deps: `pip install fastapi uvicorn pydantic numpy`
- Optional: `python scripts\build_index.py`
- Start: `uvicorn src.mh_core.api:app --reload`
- Visit: `http://127.0.0.1:8000/`

macOS/Linux (bash)
- Ensure Python: `python3 --version`
- Install deps: `pip install fastapi uvicorn pydantic numpy`
- Optional: `python3 scripts/build_index.py`
- Start: `uvicorn src.mh_core.api:app --reload`
- Visit: `http://127.0.0.1:8000/`

Notes & Tips
------------

- CORS is open for development; restrict in production.
- The frontend auto-detects its origin, so it works over tunnels and LAN.
- To share quickly, you can run `ngrok http 8000` and share the HTTPS URL.

