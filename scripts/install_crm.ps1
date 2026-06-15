# ABUZ8 LIVE CRM Installer
$ErrorActionPreference = "Stop"
$Root = ".\LIVE_CRM"
$Venv = "$Root\.venv"

Write-Host "=== ABUZ8 LIVE CRM Installer ===" -ForegroundColor Cyan

# Create venv
if (-not (Test-Path $Venv)) {
    Write-Host "Creating Python venv at $Venv ..."
    python -m venv $Venv
}

# Activate
& "$Venv\Scripts\Activate.ps1"

# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r "$Root\requirements.txt"

# Init DB
$env:PYTHONPATH = "$Root"
python -c "from app.db import init_db; init_db()"

Write-Host "Database initialized." -ForegroundColor Green

# First scan (lightweight)
Write-Host "Running first scans..."
python -c "from app.scanner_files import scan_files_incremental; print(scan_files_incremental())"
python -c "from app.scanner_models import scan_models; print(scan_models())"
python -c "from app.scanner_programs import scan_programs; print(scan_programs())"

# First monitor
Write-Host "Running first monitor..."
python -c "from app.monitor_system import capture_system_metrics; print(capture_system_metrics())"
python -c "from app.monitor_agents import discover_agents; print(discover_agents())"

# Generate reports
Write-Host "Generating reports..."
python -c "from app.valuation import run_valuation; print(run_valuation())"
python -c "from app.revenue_engine import run_revenue_engine; print(run_revenue_engine())"
python -c "from app.comfy_tracker import sync_comfy_jobs; print(sync_comfy_jobs())"
python -c "from app.context_card import generate_context_card; print('context card done')"

Write-Host "=== Install complete ===" -ForegroundColor Green
Write-Host "Run: .\scripts\run_crm.ps1" -ForegroundColor Yellow
