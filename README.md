Mental Health Chatbot (AIMhi‑Y)

A culturally safe, web‑based chatbot that guides users through the AIMhi‑Y Stay Strong plan and provides crisis support routing. Backend uses FastAPI; UI is a simple static `chat.html`.

---

Quick Start

- Requirements
  - Python 3.11+
  - pip
  - Optional: ngrok (for sharing), Ollama (local LLM), or a Gemini API key

- Create a virtual environment
  - Windows (PowerShell): `python -m venv .venv; .\.venv\Scripts\Activate.ps1`
  - macOS/Linux: `python3 -m venv .venv; source .venv/bin/activate`

- Install dependencies
  - `pip install fastapi uvicorn pydantic numpy httpx`
  - For tests: `pip install pytest`

- Configure environment
  - Copy `.env.example` to `.env` and fill values as needed. Do NOT commit `.env`.
  - To use Gemini: set `GEMINI_API_KEY`.
  - Otherwise the app uses Ollama (local LLM) if running; or it will reply minimally.
  - For email OTP in production, set SMTP vars (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`).

- Build the knowledge index (recommended)
  - `python scripts/build_index.py`
  - Produces `content/index_vectors.npy` used by retrieval.

- Run the API
  - `uvicorn src.mh_core.api:app --host 0.0.0.0 --port 8765`
  - Open `http://localhost:8765/chat.html` for the UI.

- Share via ngrok (optional)
  - `ngrok http 8765`
  - Share the `https://` URL. The UI calls the same origin.

---

Environment Variables (.env)

- LLM
  - `GEMINI_API_KEY` – use Gemini (if set)
  - `GEMINI_MODEL` – default `gemini-2.5-flash`
  - `MODEL_PROVIDER` – `gemini` (to force), otherwise auto‑selects
  - `OLLAMA_HOST` – default `127.0.0.1`
  - `OLLAMA_PORT` – default `11434`
  - `OLLAMA_MODEL` – default `llama3.2:3b-instruct-q4_K_M`

- Email/OTP (optional)
  - `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`
  - Dev helpers: `DEV_OTP_DEBUG=1`, `DEBUG_OTP=1` write OTPs to `data/outbox/*.txt`

Do not commit real API keys or passwords. `.gitignore` excludes `.env`.

---

Project Structure

- `chat.html` – Single‑page front end
- `src/mh_core/` – API, model gateway, RAG, crisis detection, style helpers
- `content/` – Knowledge snippets, indices, cultural lexicon
- `scripts/` – Build tools (`build_index.py`, ngrok helper)
- `tests/` – Basic API and crisis tests
- `otp_node/` – Optional Gmail OTP prototype (Node.js)

---

Running Tests

- `pytest -q`

---

Notes

- Crisis handling: when risk keywords are detected, the API sends a short supportive line and returns helpline options (e.g., 13YARN, Lifeline).
- Language: the assistant uses plain, respectful English (no slang). Brand names like "13YARN" remain unchanged.
