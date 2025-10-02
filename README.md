# Localized  Localized_RAG_AI Setup Guide

This guide walks through setting up all components of the Localized_RAG_AI system from scratch, including Redis, Ollama, and OCR dependencies.

## Quick Start with Docker Compose

The fastest way to get started (all platforms):
```bash
# Start Redis
docker-compose up -d

# Create Python environment & install deps
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
pip install -r requirements.txt

# Run verification script
# Windows
.\verify_setup.ps1
# Linux/Mac
./verify_setup.sh
```

## Detailed Setup by Platform

### Windows Setup

#### 1. Docker Desktop
```powershell
# Install Docker Desktop
winget install Docker.DockerDesktop

# Start Redis (if not using docker-compose)
docker run -d --name redis-stack -p 6379:6379 -p 8001:8001 redis/redis-stack:latest
```

### Linux Setup

#### 1. Docker & Docker Compose
```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get install docker-compose

# Start Redis
docker-compose up -d
```

### macOS Setup

#### 1. Docker Desktop
```bash
# Install with Homebrew
brew install --cask docker

# Start Docker Desktop, then:
docker-compose up -d
```

### 2. Ollama Setup
```powershell
# Install Ollama for Windows
winget install Ollama.Ollama

# Pull required models
ollama pull llama2        # for chat
ollama pull nomic-embed-text  # for embeddings

# Verify models
ollama list
```

### 3. OCR Dependencies (Optional)

#### Poppler (for PDF processing)
1. Download [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)
2. Extract to a permanent location (e.g., `C:\Program Files\poppler`)
3. Add to PATH or update `.env`:
```powershell
# Add to PATH
$env:Path += ";C:\Program Files\poppler\Library\bin"

# Or set in .env
POPPLER_PATH=C:\Program Files\poppler\Library\bin
```

#### Tesseract (for OCR)
1. Install [Tesseract for Windows](https://github.com/UB-Mannheim/tesseract/wiki)
2. Default install location: `C:\Program Files\Tesseract-OCR`
3. Add to PATH:
```powershell
$env:Path += ";C:\Program Files\Tesseract-OCR"
```

## Project Setup

### 1. Clone & Environment
```powershell
# Clone repository (if using version control)
git clone <repository-url>
cd Localized_RAG_AI

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Create `.env` file in project root:
```env
REDIS_URL=redis://localhost:6379/0
EMBED_MODEL=nomic-embed-text
CHAT_MODEL=llama2
POPPLER_PATH=C:\Program Files\poppler\Library\bin
```

## Verification Steps

### 1. Test Redis Connection
```powershell
# Start Python REPL
python
>>> import redis
>>> r = redis.from_url("redis://localhost:6379/0")
>>> r.ping()
True  # Should return True
```

### 2. Test Ollama
```powershell
# Start Python REPL
python
>>> import ollama
>>> response = ollama.embeddings(model="nomic-embed-text", prompt="test")
>>> len(response["embedding"])  # Should return embedding dimension
```

### 3. Test PDF Processing
```powershell
# From project root
python -c "from utils.pdf_loader import load_pdf_with_ocr; print(load_pdf_with_ocr('data/heavy-duty.pdf'))"
```

## Troubleshooting

### Redis Issues
- Ensure Docker is running
- Check container: `docker ps -a`
- View logs: `docker logs redis-stack`
- Reset: `docker restart redis-stack`

### Ollama Issues
- Check service: `ollama serve`
- Pull models again if needed
- View logs in Ollama desktop app

### OCR Issues
- Verify Poppler path in `.env`
- Check Tesseract installation: `tesseract --version`
- Try sample PDF with `--allow-ocr` flag
- Common error: "pytesseract not found" means Tesseract isn't in PATH

## Running the System

Start the interactive CLI:
```bash
python main.py --allow-ocr
```

### Example Workflows

#### 1. Basic Document Loading
```
Select an option:
2  # Load documents
Enter file paths to load: data/heavy-duty.pdf
✅ Done loading. 1 namespaces loaded.
Type 'chat' to ask questions: chat
Search scope: (a)ll or (l)oaded? [a/l]: l

Ask a question: What maintenance is required?
```

#### 2. Multiple Document Chat
```
Select an option:
2  # Load documents
Enter file paths to load: data/manual1.pdf, data/manual2.pdf
✅ Done loading. 2 namespaces loaded.
Type 'chat' to ask questions: chat

Ask a question: Compare the procedures in both manuals
```

#### 3. JSON Data with Key Selection
```
Select an option:
2  # Load documents
Enter file paths to load: data/training_splits.json
❌ Top-level JSON is an object. Use --json-key
Enter file paths to load: data/training_splits.json --json-key exercises
✅ Done loading. 1 namespaces loaded.
```

#### 4. OCR Fallback Example
```
Select an option:
2  # Load documents
Enter file paths to load: data/scanned.pdf
⚠️ No text extracted from PDF, trying OCR fallback...
📄 Extracted text from 5/5 pages
```

For development, you can monitor:
- Redis: http://localhost:8001 (RedisInsight web UI)
- Docker: Docker Desktop dashboard or `docker stats`
- Ollama: Activity in desktop app or `ollama serve` output
