## Copilot / AI Agent Instructions — RAG_AI

Purpose: Guide AI agents through the RAG_AI codebase architecture, data flows, and project-specific patterns.

Key files and flows
- `main.py` — CLI entry point for document ingestion and queries; manages embedding pipeline
- `utils/helpers.py` — Core utilities: `sha256_of_file()`, smart JSON loading, PDF wrapper
- `utils/pdf_loader.py` — PDF text extraction with OCR fallback via `pdf2image` + `pytesseract`
- `utils/text_splitter.py` — Semantic chunking with 1000-char chunks and 200-char overlap

Data pipeline
1. `load_or_build_vectors()` namespaces docs by SHA256 hash
2. Documents split into semantic chunks (paragraphs/sections)
3. Chunks embedded via `ollama.embeddings(model=EMBED_MODEL)`
4. Vectors stored in Redis: `docs:{file_hash}:{index}` with fields:
   - `text`: UTF-8 content
   - `vector`: float32 bytes (use `np.frombuffer(dtype=np.float32)` to read)
5. Query flow: embed query → cosine similarity search → join top-k chunks → Ollama chat

Setup & run
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py --allow-ocr  # Interactive CLI
```

Project patterns
- PDF loading tries text extract then OCR fallback if needed
- JSON auto-detects single list in dict, else needs `--json-key`
- Vector similarity uses dot product with zero-denom guard
- Windows OCR needs Poppler path (see `.env.example`)
- Interactive CLI stores loaded docs for scoped queries

Gotchas (discovered)
- `text_splitter.py::_clean_text()` collapses newlines before normalizing paragraphs
- OCR deps (`pdf2image`, `pytesseract`) are optional—code handles missing gracefully


