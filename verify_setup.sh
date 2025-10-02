#!/bin/bash
# Verification script for Linux/Mac

print_status() {
    if [ $? -eq 0 ]; then
        echo "✅ $1"
    else
        echo "❌ $1"
    fi
}

echo -e "\n🔍 Checking RAG_AI dependencies...\n"

# Check Python environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    print_status "Virtual environment found and activated"
else
    print_status "Virtual environment not found. Run: python -m venv .venv"
fi

# Check Docker and Redis
docker ps --filter "name=redis-stack" --format "{{.Status}}" | grep "Up" > /dev/null
print_status "Redis container status"

# Check Ollama
if command -v ollama >/dev/null; then
    ollama list | grep -E "llama2|nomic-embed-text" > /dev/null
    print_status "Required Ollama models"
else
    print_status "Ollama not installed"
fi

# Check OCR Dependencies
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    brew list poppler > /dev/null
    print_status "Poppler (brew)"
    
    brew list tesseract > /dev/null
    print_status "Tesseract (brew)"
else
    # Linux
    dpkg -l | grep -q poppler-utils
    print_status "Poppler (apt)"
    
    dpkg -l | grep -q tesseract-ocr
    print_status "Tesseract (apt)"
fi

# Check .env file
if [ -f ".env" ]; then
    print_status ".env file found"
else
    print_status ".env file missing. Copy .env.example to .env and update values"
fi

# Try Python imports
echo -e "\n🐍 Checking Python dependencies...\n"

modules=("redis" "numpy" "ollama" "PyPDF2" "pdf2image" "pytesseract" "python-dotenv")

for module in "${modules[@]}"; do
    python -c "import $module" 2>/dev/null
    print_status "Module $module"
done

echo -e "\n💡 Next steps:"
echo "1. Run example: python main.py --allow-ocr"
echo "2. Load a sample document from data/"
echo "3. Try querying with option 3"