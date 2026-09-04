# ============================================================
# CurrencyX AI - Development Startup Script
# ------------------------------------------------------------
# Starts the FastAPI backend (port 8000) and the Vite frontend
# in separate windows, using the project's existing virtualenv.
#
# Usage (from the repository root):
#   powershell -ExecutionPolicy Bypass -File .\start-dev.ps1
#
# If PowerShell blocks scripts, run the command above - the
# -ExecutionPolicy Bypass flag applies only to this invocation.
#
# Stop both services later with: .\stop-dev.ps1
# No secrets are read or printed by this script.
# ============================================================

$ErrorActionPreference = "Stop"

$root     = $PSScriptRoot
$backend  = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

$venvPython = Join-Path $backend "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Backend venv not found at: $venvPython" -ForegroundColor Red
    Write-Host "        Create it first, or adjust this script to your Python setup."
    exit 1
}
if (-not (Test-Path (Join-Path $frontend "package.json"))) {
    Write-Host "[ERROR] Frontend not found at: $frontend" -ForegroundColor Red
    exit 1
}

# PID bookkeeping (in TEMP so nothing is written into the repository).
$pidFile = Join-Path $env:TEMP "currencyx-dev-pids.json"

# --- Backend -------------------------------------------------------------
Write-Host "[1/2] Starting FastAPI backend on port 8000 ..." -ForegroundColor Cyan
$backendProc = Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "main:app", "--port", "8000" `
    -WorkingDirectory $backend `
    -WindowStyle Minimized -PassThru

# --- Frontend ------------------------------------------------------------
Write-Host "[2/2] Starting Vite frontend ..." -ForegroundColor Cyan
$frontendProc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm run dev" `
    -WorkingDirectory $frontend `
    -WindowStyle Minimized -PassThru

@{
    backend  = $backendProc.Id
    frontend = $frontendProc.Id
    started  = (Get-Date).ToString("o")
} | ConvertTo-Json | Set-Content -Path $pidFile -Encoding UTF8

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " CurrencyX AI development environment is starting" -ForegroundColor Green
Write-Host "   Backend  : http://127.0.0.1:8000  (docs: /docs, health: /health, ready: /ready)" -ForegroundColor Green
Write-Host "   Frontend : http://localhost:5173  (Vite prints the actual port if 5173 is busy)" -ForegroundColor Green
Write-Host "   PIDs saved to: $pidFile" -ForegroundColor Gray
Write-Host "   Stop everything with: .\stop-dev.ps1" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend PID: $($backendProc.Id)   Frontend launcher PID: $($frontendProc.Id)"