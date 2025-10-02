# PowerShell script to verify RAG_AI setup
param(
    [string]$PopplerPath = "C:\Program Files\poppler\Library\bin",
    [string]$TesseractPath = "C:\Program Files\Tesseract-OCR"
)

function Write-Status {
    param($Message, $Success)
    if ($Success) {
        Write-Host "[OK] $Message" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $Message" -ForegroundColor Red
    }
}

Write-Host "`n[Checking RAG_AI dependencies...]`n" -ForegroundColor Cyan

# Check Python environment
try {
    $venvPath = ".venv\Scripts\activate.ps1"
    if (Test-Path $venvPath) {
        . $venvPath
        Write-Status "Virtual environment found and activated" $true
    } else {
        Write-Status "Virtual environment not found. Run: python -m venv .venv" $false
    }
} catch {
    Write-Status "Error activating virtual environment" $false
}

# Check Docker and Redis
try {
    $docker = docker ps --filter "name=redis-stack" --format "{{.Status}}"
    if ($docker -match "Up") {
        Write-Status "Redis container is running" $true
    } else {
        Write-Status "Redis container not found. Run: docker-compose up -d" $false
    }
} catch {
    Write-Status "Docker not running or not installed" $false
}

# Check Ollama
try {
    $ollama = ollama list
    if ($ollama -match "llama2" -and $ollama -match "nomic-embed-text") {
        Write-Status "Required Ollama models found" $true
    } else {
        Write-Status "Missing Ollama models. Run: ollama pull llama2 nomic-embed-text" $false
    }
} catch {
    Write-Status "Ollama not running or not installed" $false
}

# Check OCR Dependencies
if (Test-Path $PopplerPath) {
    Write-Status "Poppler found at: $PopplerPath" $true
} else {
    Write-Status "Poppler not found. Download from: github.com/oschwartz10612/poppler-windows/releases/" $false
}

if (Test-Path $TesseractPath) {
    Write-Status "Tesseract found at: $TesseractPath" $true
} else {
    Write-Status "Tesseract not found. Download from: github.com/UB-Mannheim/tesseract/wiki" $false
}

# Check .env file
if (Test-Path ".env") {
    Write-Status ".env file found" $true
} else {
    Write-Status ".env file missing. Copy .env.example to .env and update values" $false
}

# Try Python imports
Write-Host "`n[Checking Python dependencies...]`n" -ForegroundColor Cyan

$modules = @(
    "redis",
    "numpy",
    "ollama",
    "PyPDF2",
    "pdf2image",
    "pytesseract",
    "dotenv"
)

foreach ($module in $modules) {
    $cmd = "import importlib; importlib.import_module('$module')"
    python -c $cmd 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Status "Module $module installed" $true
    } else {
        Write-Status "Module $module missing. Run: pip install -r requirements.txt" $false
    }
}

Write-Host ''
Write-Host 'Next steps:' -ForegroundColor Yellow
Write-Host '1. Run example: python main.py --allow-ocr'
Write-Host '2. Load a sample document from data/'
Write-Host '3. Try querying with option 3'