import json, http.client, os
from functools import lru_cache
import numpy as np
from pathlib import Path

EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
VECS = Path("content/index_vectors.npy")
META = Path("content/index_meta.json")

_vectors = None
_meta = None

@lru_cache(maxsize=256)
def _embed_one(text: str):
    """Embed a single text with Ollama. Handles 'embedding' and 'embeddings' keys."""
    conn = http.client.HTTPConnection("127.0.0.1", 11434, timeout=15)
    payload = {"model": EMBED_MODEL, "input": text}
    conn.request("POST", "/api/embeddings", body=json.dumps(payload), headers={"Content-Type":"application/json"})
    resp = conn.getresponse()
    raw = resp.read().decode("utf-8", errors="ignore")
    conn.close()

    obj = json.loads(raw)
    if "embedding" in obj and isinstance(obj["embedding"], list):
        v = np.array(obj["embedding"], dtype="float32")
    elif "embeddings" in obj and isinstance(obj["embeddings"], list) and obj["embeddings"]:
        v = np.array(obj["embeddings"][0], dtype="float32")
    else:
        v = np.random.normal(size=(384,)).astype("float32")
    v = v / (np.linalg.norm(v) + 1e-9)
    return v

def _load_index():
    global _vectors, _meta
    if _vectors is None:
        if not VECS.exists() or not META.exists():
            raise FileNotFoundError("Missing index files. Run:  python scripts\\build_index.py")
        _vectors = np.load(VECS)
        _meta = json.loads(META.read_text(encoding="utf-8"))

def retrieve_context(user_text: str, k: int = 1) -> str:
    # For very short inputs, skip retrieval to reduce latency
    if not user_text or len(user_text.strip()) < 12:
        return ""
    _load_index()
    q = _embed_one(user_text)
    sims = (_vectors @ q).tolist()
    top = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:k]
    snippets = [_meta[i]["text"] for i in top]
    return "\n".join(f"- {s}" for s in snippets)
