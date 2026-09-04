# ============================================================
# CurrencyX AI - Development Stop Script
# ------------------------------------------------------------
# Stops only the backend/frontend processes recorded by
# start-dev.ps1 (PIDs saved in %TEMP%\currencyx-dev-pids.json).
# It never kills unrelated Python or Node processes.
#
# Usage: .\stop-dev.ps1
# ============================================================

$ErrorActionPreference = "SilentlyContinue"

$pidFile = Join-Path $env:TEMP "currencyx-dev-pids.json"

if (-not (Test-Path $pidFile)) {
    Write-Host "No dev PID file found ($pidFile)." -ForegroundColor Yellow
    Write-Host "Nothing to stop - or the services were started manually."
    exit 0
}

$records = Get-Content $pidFile -Raw | ConvertFrom-Json

function Stop-DevProcess {
    param([int]$Id, [string]$Label)

    $proc = Get-Process -Id $Id -ErrorAction SilentlyContinue
    if (-not $proc) {
        Write-Host "$Label (PID $Id): already stopped." -ForegroundColor Gray
        return
    }
    Stop-Process -Id $Id -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
    if (Get-Process -Id $Id -ErrorAction SilentlyContinue) {
        Write-Host "$Label (PID $Id): failed to stop." -ForegroundColor Red
    } else {
        Write-Host "$Label (PID $Id): stopped." -ForegroundColor Green
    }
}

# The frontend launcher is cmd.exe - stopping it leaves the node/vite
# child running, so stop any node.exe listening on Vite's dev port too.
Stop-DevProcess -Id $records.frontend -Label "Frontend launcher"
Stop-DevProcess -Id $records.backend  -Label "Backend"

# Targeted cleanup: node processes still listening on Vite dev ports.
Get-NetTCPConnection -LocalPort 5173,5174 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    ForEach-Object {
        $p = Get-Process -Id $_ -ErrorAction SilentlyContinue
        if ($p -and $p.ProcessName -eq "node") {
            Stop-DevProcess -Id $_ -Label "Vite (node)"
        }
    }

# Targeted cleanup: uvicorn still listening on port 8000 started from our venv.
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    ForEach-Object {
        $p = Get-CimInstance Win32_Process -Filter "ProcessId=$_" -ErrorAction SilentlyContinue
        if ($p -and $p.CommandLine -like "*uvicorn main:app*") {
            Stop-DevProcess -Id $_ -Label "Uvicorn"
        }
    }

Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
Write-Host "Development environment stopped." -ForegroundColor Cyan