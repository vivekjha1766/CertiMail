# CertiMail Startup Script (PowerShell)
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      CertiMail - Certificate Distribution Dashboard    " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.10+."
    exit 1
}

# Check npm
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js / npm is not installed or not in PATH. Please install Node.js (v18+)."
    exit 1
}

# Setup venv if missing
if (-not (Test-Path ".venv")) {
    Write-Host "[SETUP] Creating Python virtual environment (.venv)..." -ForegroundColor Yellow
    python -m venv .venv
}

# Install dependencies
Write-Host "[SETUP] Verifying Python dependencies..." -ForegroundColor Yellow
& .\.venv\Scripts\pip install -q -r requirements.txt

if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "[SETUP] Installing frontend npm dependencies..." -ForegroundColor Yellow
    Push-Location frontend
    npm install
    Pop-Location
}

# Start Backend
Write-Host "[LAUNCH] Starting FastAPI backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '.\.venv\Scripts\python' -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

# Start Frontend
Write-Host "[LAUNCH] Starting Vite frontend on http://localhost:5173 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "CertiMail is running!" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "Backend API Docs: http://127.0.0.1:8000/docs" -ForegroundColor White
