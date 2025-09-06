import json, os, http.client, numpy as np
from pathlib import Path

EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")  # Ollama embedding model
KNOW_PATH = Path("content/knowledge")
OUT_VECS = Path("content/index_vectors.npy")
OUT_META = Path("content/index_meta.json")

def _embed_one(text: str):
    """Embed a single text with Ollama. Handles both 'embedding' and 'embeddings'."""
    conn = http.client.HTTPConnection("127.0.0.1", 11434, timeout=60)
    payload = {"model": EMBED_MODEL, "input": text}
    conn.request("POST", "/api/embeddings", body=json.dumps(payload), headers={"Content-Type":"application/json"})
    resp = conn.getresponse()
    raw = resp.read().decode("utf-8", errors="ignore")
    conn.close()
    obj = json.loads(raw)
    if "embedding" in obj and isinstance(obj["embedding"], list):
        return np.array(obj["embedding"], dtype="float32")
    if "embeddings" in obj and isinstance(obj["embeddings"], list) and obj["embeddings"]:
        return np.array(obj["embeddings"][0], dtype="float32")
    raise RuntimeError(f"Unexpected embeddings response: {raw[:300]}")

def load_snippets():
    items=[]
    for p in KNOW_PATH.glob("*.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            items.append({
                "id": rec["id"],
                "text": rec["text"],
                "topic": rec.get("topic","")
            })
    if not items:
        raise SystemExit(f"No snippets found in {KNOW_PATH} (*.jsonl). Add some lines and re-run.")
    return items

def main():
    KNOW_PATH.mkdir(parents=True, exist_ok=True)
    items = load_snippets()
    vecs = []
    for it in items:
        v = _embed_one(it["text"])
        v = v / (np.linalg.norm(v) + 1e-9)
        vecs.append(v)
    vecs = np.stack(vecs).astype("float32")
    np.save(OUT_VECS, vecs)
    OUT_META.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexed {len(items)} snippets → {OUT_VECS} & {OUT_META}")

if __name__ == "__main__":
    main()
