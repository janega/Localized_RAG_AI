import json
import hashlib
import redis
import numpy as np
from tqdm import tqdm
import argparse
from pathlib import Path
import ollama
import os
from dotenv import load_dotenv
from utils.helpers import load_pdf, load_json, load_pdf_with_ocr

# -------------------
# Load environment variables
# -------------------
load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama2")

# -------------------
# Redis connection
# -------------------
r = redis.from_url(REDIS_URL)

# -------------------
# Helpers
# -------------------
def compute_hash(file_path: str) -> str:
    """Create a hash of the file contents for cache invalidation."""
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def embed_text(text: str) -> np.ndarray:
    """Get vector embedding using Ollama."""
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return np.array(response["embedding"], dtype=np.float32)

def store_embeddings(redis_client, key_prefix, data):
    """Store embeddings in Redis if not already present."""
    for i, entry in enumerate(tqdm(data, desc="Embedding entries")):
        # Handle both string (PDF) and dict (JSON) entries
        text = entry if isinstance(entry, str) else json.dumps(entry)
        vector = embed_text(text)
        redis_client.hset(f"{key_prefix}:{i}", mapping={
            "text": text,
            "vector": vector.tobytes()
        })

def load_or_build_vectors(file_path: str, allow_ocr: bool = False):
    """Smartly load or build vectors from JSON or PDF."""
    file_hash = compute_hash(file_path)
    key_prefix = f"docs:{file_hash}"

    # If already cached in Redis, skip rebuilding
    if r.exists(f"{key_prefix}:0"):
        print(f"Found existing embeddings in Redis for {file_path}, skipping rebuild.")
        return key_prefix

    # Load data based on file type
    file_path_obj = Path(file_path)
    if file_path_obj.suffix.lower() == '.pdf':
        data = load_pdf(str(file_path_obj))
        if (not data or len(data) == 0) and allow_ocr:
            print("⚠️  No text extracted from PDF, trying OCR fallback...")
            data = load_pdf_with_ocr(str(file_path_obj))
        print(f"📄 Loaded {len(data) if data else 0} text chunks from PDF")
    else:
        data = load_json(str(file_path_obj))
        print(f"📄 Loaded {len(data) if data else 0} entries from JSON")

    if not data:
        raise ValueError(f"No data could be extracted from {file_path_obj}")

    print("⚡ Building embeddings...")
    store_embeddings(r, key_prefix, data)
    return key_prefix

def _iter_keys_for_prefixes(prefixes):
    """Yield redis keys for given prefix(es)."""
    if prefixes is None:
        pattern = "docs:*:*"
        for k in r.scan_iter(pattern):
            yield k
    elif isinstance(prefixes, str):
        pattern = f"{prefixes}:*"
        for k in r.scan_iter(pattern):
            yield k
    elif isinstance(prefixes, (list, tuple, set)):
        for p in prefixes:
            pattern = f"{p}:*"
            for k in r.scan_iter(pattern):
                yield k
    else:
        return

def query_redis(key_prefixes, query, top_k=3):
    """Search Redis for closest notes to query.
    key_prefixes can be:
      - None -> search all docs
      - string -> single namespace
      - list -> multiple namespaces
    """
    q_vector = embed_text(query)

    scores = []
    seen_keys = set()
    for key in _iter_keys_for_prefixes(key_prefixes):
        if key in seen_keys:
            continue
        seen_keys.add(key)
        entry = r.hgetall(key)
        if not entry:
            continue
        text = entry.get(b"text")
        vector_bin = entry.get(b"vector")
        if not text or not vector_bin:
            continue
        text = text.decode("utf-8")
        vector = np.frombuffer(vector_bin, dtype=np.float32)

        # cosine similarity
        denom = (np.linalg.norm(q_vector) * np.linalg.norm(vector))
        score = float(np.dot(q_vector, vector) / denom) if denom != 0 else 0.0
        scores.append((score, text))

    scores.sort(reverse=True, key=lambda x: x[0])
    return scores[:top_k]

def ask(query, key_prefixes=None):
    """Run a query and pass context to LLM.
    key_prefixes: None -> search all; string/list -> search specific namespaces
    """
    results = query_redis(key_prefixes, query)
    if not results:
        return "No relevant documents found."

    context = "\n".join([res[1] for res in results])

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "Act as a world-class assistant with deep expertise across multiple domains. Respond using only the provided context and any directly relevant knowledge. Do not invent, speculate, or rely on external assumptions. Prioritize accuracy, relevance, and clarity in every answer"},
            {"role": "user", "content": f"Use this context:\n{context}\n\nQuestion: {query}"}
        ],
    )
    return response["message"]["content"]

# -------------------
# Main interactive flow
# -------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG-based Q&A system")
    parser.add_argument("--allow-ocr", action="store_true", help="Allow OCR fallback for PDFs when loading")
    args = parser.parse_args()

    loaded_prefixes = []  # track prefixes loaded in this session

    def interactive_load(allow_ocr=False):
        print("\nEnter file paths to load. You can enter multiple paths separated by commas,")
        print("or enter one path per line and type 'done' when finished.")
        print("\nExamples (shown only when you choose option 2):")
        print(r"  Single:  d:\My Coding Projects\Python\RAG_AI\data\training_splits.json")
        print(r"  Multiple: d:\My Coding Projects\Python\RAG_AI\data\training_splits.json, d:\My Coding Projects\Python\RAG_AI\data\other_doc.pdf")
        while True:
            inp = input("\nPath (or 'done' to finish): ").strip()
            if inp.lower() == "done":
                break
            # allow comma-separated
            paths = [p.strip() for p in inp.split(",") if p.strip()]
            for p in paths:
                try:
                    if not Path(p).exists():
                        print(f"❌ Path not found: {p}")
                        continue
                    prefix = load_or_build_vectors(p, allow_ocr=allow_ocr)
                    if prefix not in loaded_prefixes:
                        loaded_prefixes.append(prefix)
                except Exception as e:
                    print(f"❌ Failed to load {p}: {e}")

    while True:
        print("\nSelect an option:")
        print("1) Chat now (search all embeddings)")
        print("2) Load documents")
        print("3) Chat with only currently loaded documents")
        print("4) Show loaded document namespaces")
        print("5) Exit")
        choice = input("Choice (1-5): ").strip()

        if choice == "1":
            # Chat searching across all embeddings
            while True:
                q = input("\nAsk a question (or type 'back' to main menu): ").strip()
                if q.lower() in ("back", "exit"):
                    break
                answer = ask(q, key_prefixes=None)
                print("\n🤖 Answer:", answer)

        elif choice == "2":
            interactive_load(allow_ocr=args.allow_ocr)
            print(f"✅ Done loading. {len(loaded_prefixes)} namespaces loaded.")
            # after loading allow user to continue adding or go chat
            while True:
                nxt = input("Type 'add' to load more, 'chat' to ask questions, or 'back' to main menu: ").strip().lower()
                if nxt == "add":
                    interactive_load(allow_ocr=args.allow_ocr)
                elif nxt == "chat":
                    # chat either across loaded prefixes or all
                    scope = input("Search scope: (a)ll or (l)oaded? [a/l]: ").strip().lower()
                    kp = None if scope != "l" else loaded_prefixes
                    while True:
                        q = input("\nAsk a question (or type 'back' to stop): ").strip()
                        if q.lower() in ("back", "exit"):
                            break
                        answer = ask(q, key_prefixes=kp)
                        print("\n🤖 Answer:", answer)
                    break
                elif nxt == "back":
                    break
                else:
                    print("Unknown option. Use 'add', 'chat', or 'back'.")

        elif choice == "3":
            if not loaded_prefixes:
                print("No documents loaded in this session. Use option 2 to load documents first.")
                continue
            while True:
                q = input("\nAsk a question (or type 'back' to main menu): ").strip()
                if q.lower() in ("back", "exit"):
                    break
                answer = ask(q, key_prefixes=loaded_prefixes)
                print("\n🤖 Answer:", answer)

        elif choice == "4":
            if not loaded_prefixes:
                print("No namespaces loaded in this session.")
            else:
                print("Loaded namespaces:")
                for p in loaded_prefixes:
                    print(" -", p)

        elif choice == "5" or choice.lower() == "exit":
            print("Goodbye.")
            break

        else:
            print("Invalid choice. Enter a number 1-5.")
# ...existing code...