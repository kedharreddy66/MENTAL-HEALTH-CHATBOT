# Gemini Setup

This project can use Google Generative AI (Gemini) for responses instead of the local Ollama model.

## Steps

1) Get an API key
- Sign up at https://ai.google.dev/ and create an API key.

2) Configure environment
- Create a `.env` at the project root (copy `.env.example`).
- Set:
  - `GEMINI_API_KEY=your_api_key`
  - Optional: `GEMINI_MODEL=gemini-2.5-flash` (default)
  - Optional: `MODEL_PROVIDER=gemini` to force Gemini by default

3) Run the API
- Example (FastAPI with uvicorn):
  - `uvicorn src.mh_core.api:app --reload`

4) Use from the UI
- Open `chat.html`.
- The UI auto-selects Gemini if the backend reports it is available; you can also toggle the “Model” button.

## Notes
- Backend also auto-prefers Gemini whenever `GEMINI_API_KEY` is present (even without `MODEL_PROVIDER=gemini`).
- Check `/debug/providers` to verify provider availability.
- If no API key is set, the app falls back to the local Ollama configuration.
