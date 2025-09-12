# 🧠 MENTAL‑HEALTH‑CHATBOT

A culturally safe, web‑based chatbot designed to deliver the four‑step Stay Strong plan and provide mental‑health support for Aboriginal and Torres Strait Islander youth. Developed by Team 12 at Charles Darwin University, this prototype complements the AIMhi‑Y initiative by offering anonymous, accessible check‑ins and crisis support while respecting cultural protocols.

---

## 🌟 Project Goals
- **Culturally tailored support:** Translate the Stay Strong plan into a structured dialogue that uses strengths‑based language and plain English.
- **Accessible chat interface:** Provide a responsive conversation flow via a simple HTML page ([chat.html](chat.html)) that users can open in a browser.
- **Crisis keyword detection:** Monitor for risk‑related phrases and immediately display helpline information relevant to Indigenous youth.
- **Privacy by design:** Operate locally without storing or transmitting personal data.
- **Curated knowledge base:** Leverage AIMhi manuals, self‑care posters, training videos, and other approved resources to inform responses.

---

## 🚀 Features
- **Rule‑first conversation flow:** Structured JSON files guide every step (family/strengths → worries → goals → actions), ensuring cultural safety.
- **Crisis module:** A keyword scanner triggers a helpline panel when phrases like “suicide” or “not safe” are detected.
- **Retrieval‑augmented responses:** A small local language model (Llama 3.2) generates context‑aware replies using culturally relevant snippets from the knowledge base.
- **Modular architecture:** Python FastAPI powers the backend, while a lightweight HTML front‑end makes integration simple.
- **Cultural oversight:** All scripts and prompts are reviewed by Indigenous health professionals to maintain respect and relevance.

---

## 🗂️ Repository Structure

```
MENTAL-HEALTH-CHATBOT/
├── chat.html          # Single-page front‑end interface
├── src/
│   └── mh_core/       # Core backend package (FastAPI + helpers)
│       ├── api.py                 # FastAPI endpoints (/health, /reset, /chat)
│       ├── ai_gateway.py          # Ollama chat gateway + system prompt
│       ├── rag.py                 # Retrieval (Ollama embeddings + local index)
│       ├── models.py              # Pydantic request/response models
│       ├── crisis.py              # Crisis keyword signal detection
│       ├── culture.py             # Normalisation + lexicon support
│       ├── safety.py              # Output safety filters (non‑crisis)
│       ├── audit.py               # Simple trace/audit helpers
│       ├── flow.py                # Conversation step helpers (optional)
│       └── content_loader.py      # Utilities for loading content (optional)
├── scripts/
│   ├── build_index.py             # Build vector index used by rag.py
│   ├── chat_cli.py                # Simple terminal client (optional)
│   ├── extract_pdf_text.py        # Utilities for preparing content (optional)
│   └── build_tuning_dataset.py    # Create instruction‑tuning dataset (optional)
├── content/           # Knowledge base, style guide, indices
├── tuning/            # Tuning dataset(s) for experimentation
├── tests/             # Unit tests for API, crisis detection, flow
├── .gitignore         # Excludes venvs, caches, build artifacts
└── README.md          # Project overview (this file)
```

---

## 🧩 Key Modules
- `src/mh_core/api.py` – Implements the FastAPI application with `/health` and `/chat` endpoints. The `/chat` endpoint receives user messages and state, retrieves context using RAG, calls the local LLM, and returns the reply.
- `src/mh_core/ai_gateway.py` – Manages the connection to the local LLM and defines a system prompt that enforces culturally safe, strengths‑based responses.
- `src/mh_core/crisis.py` – Detects crisis keywords using regex patterns; triggers helpline messages when not in development mode.
- `src/mh_core/flow.py` – Manages conversation steps (strengths → worries → goals → support) based on the current ChatState.
- `src/mh_core/language_style.py` – Adjusts LLM responses into plain, culturally resonant language.
- `src/mh_core/rag.py` – Handles retrieval of relevant context snippets by embedding user input and comparing it against pre‑built vector indices.

---

## ⚙️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kedharreddy66/MENTAL-HEALTH-CHATBOT.git
   cd MENTAL-HEALTH-CHATBOT
   ```
2. **(Optional) Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```
3. **Install dependencies:**
   This repo does not currently include a `requirements.txt`. Install the minimal runtime deps:
   ```bash
   pip install fastapi uvicorn pydantic numpy
   # Optional (for scripts): pdfminer.six
   # If using lint/tests locally: pytest ruff mypy
   ```
4. **Build the embeddings index (if needed):**
   ```bash
   python3 scripts/build_index.py
   ```
5. **Run the backend:**
   ```bash
   uvicorn src.mh_core.api:app --reload
   ```

The API will start at http://localhost:8000.

**Open `chat.html` in your browser** to use the chatbot. It sends requests to the API’s `/chat` endpoint to drive the conversation.

---

## 💡 Usage
- Start a conversation by typing into the chat box on `chat.html`. The bot guides you through the four Stay Strong steps.
- If distressing keywords (e.g., “suicide,” “hurt myself,” “not safe”) are detected, the chat flow pauses and a helpline panel is displayed.
- When the conversation ends, the bot generates a summary plan of strengths, worries, goals, and actions.

---

## 🔧 Configuration

- Ollama settings (local LLM):
  - `OLLAMA_HOST` (default `127.0.0.1`)
  - `OLLAMA_PORT` (default `11434`)
  - `OLLAMA_MODEL` (default `llama3.2:3b-instruct-q4_K_M`)
  - `OLLAMA_NUM_THREADS` (optional, integer)
- App behaviour toggles:
  - `PLAIN_ENGLISH_MODE` = `true|false` (default `true`)
  - `FAST_MODE` = `true|false` (default `true` – skip retrieval for speed)
- Local style guide: add `content/style_guide_local.json` with an `{"append": "..."}` field to append guidance to the system prompt.

Tip (Windows): if running Ollama elsewhere, set `OLLAMA_HOST` to that machine’s IP and keep port open.

---

## 🔁 Development Workflow
This project uses an Agile‑inspired process:

1. **Research & framing:** Review AIMhi resources and similar chatbots to create a content matrix.
2. **Conversation & UI design:** Build JSON dialogue and prototype the chat interface.
3. **Implementation:** Develop the backend, front‑end, and crisis detection module.
4. **Integration & hardening:** Connect helplines, generate summary plans, and ensure accessibility.
5. **Testing & iteration:** Conduct usability tests and refine prompts.
6. **Documentation & delivery:** Write user and technical guides and prepare final presentations.

---

## 🤝 Contributing
We welcome contributions that align with the project’s cultural and ethical guidelines.

1. Fork this repository and create a feature or bug‑fix branch.
2. Ensure your changes respect cultural protocols and maintain user safety.
3. Run the unit tests (`pytest`) to verify that crisis detection and helpline triggers work.
4. Submit a pull request describing your changes and why they’re needed.

---

## 🙏 Acknowledgements
This chatbot draws on the AIMhi Stay Strong framework developed by the Menzies School of Health Research. We thank our supervisor, Dr Cat Kutay, for guidance on cultural safety and methodology, and we acknowledge the Indigenous youth, elders, and health professionals who contributed through workshops and feedback.

---

## 📄 License
This project is currently unlicensed. Please contact the repository owner for licensing information.

---

## 🧹 Housekeeping (.gitignore)
- Virtual environments (`.venv/`, `venv/`, `conda-env/`) and Python caches (`__pycache__/`, `*.pyc`) are ignored.
- If you previously committed environment files, run:
  ```bash
  git rm -r --cached .venv conda-env **/__pycache__
  git commit -m "Clean tracked env/cache files"
  ```
