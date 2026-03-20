import json
import uuid
from pathlib import Path
from math import sqrt

BASE_DIR = Path(__file__).resolve().parent
MEM_FILE = BASE_DIR / "data" / "memory_vectors.json"
MEM_FILE.parent.mkdir(parents=True, exist_ok=True)

# --- Simple placeholder embedding for demonstration ---
def embed_text(text):
    # Convert text to vector of char codes / length
    vec = [ord(c) for c in text][:50]  # limit vector size
    vec += [0]*(50-len(vec))
    return vec

# --- Cosine similarity ---
def cosine_sim(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    mag_a = sqrt(sum(x*x for x in a))
    mag_b = sqrt(sum(y*y for y in b))
    return dot / (mag_a*mag_b + 1e-8)

# --- Load / Save ---
def load_memory():
    if MEM_FILE.exists():
        with open(MEM_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    return []

def save_memory(mem):
    with open(MEM_FILE,"w",encoding="utf-8") as f:
        json.dump(mem,f,indent=2)

# --- Store memory with embedding ---
def store_memory(text):
    mem = load_memory()
    mem.append({
        "id": str(uuid.uuid4()),
        "text": text,
        "embedding": embed_text(text)
    })
    save_memory(mem)
    return True

# --- Semantic search ---
def search_memory(query, top_k=5):
    query_vec = embed_text(query)
    mem = load_memory()
    scored = []
    for m in mem:
        sim = cosine_sim(query_vec, m.get("embedding",[0]*50))
        scored.append((sim,m))
    scored.sort(reverse=True, key=lambda x:x[0])
    return [m for _,m in scored[:top_k]]