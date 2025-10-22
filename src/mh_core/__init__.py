# Auto-load environment variables from a project-root .env file if present,
# without adding external dependencies. This runs once on package import.
try:
    from .env import load_dotenv_if_present as _load_env
    _load_env()
except Exception:
    # Non-fatal: continue with normal environment.
    pass
