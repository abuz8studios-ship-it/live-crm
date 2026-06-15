# ABUZ8 CRM Scan Now
$Root = ".\LIVE_CRM"
$Venv = "$Root\.venv"
& "$Venv\Scripts\Activate.ps1"
$env:PYTHONPATH = "$Root"

Write-Host "=== Scanning Files ===" -ForegroundColor Cyan
python -c "from app.scanner_files import scan_files_incremental; print(scan_files_incremental())"
Write-Host "=== Scanning Models ===" -ForegroundColor Cyan
python -c "from app.scanner_models import scan_models; print(scan_models())"
Write-Host "=== Scanning Programs ===" -ForegroundColor Cyan
python -c "from app.scanner_programs import scan_programs; print(scan_programs())"
Write-Host "=== Updating Revenue ===" -ForegroundColor Cyan
python -c "from app.revenue_engine import run_revenue_engine; print(run_revenue_engine())"
Write-Host "=== Updating Context Card ===" -ForegroundColor Cyan
python -c "from app.context_card import generate_context_card; print('done')"
Write-Host "=== Scan complete ===" -ForegroundColor Green
