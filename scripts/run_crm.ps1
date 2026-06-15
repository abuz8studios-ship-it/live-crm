# ABUZ8 LIVE CRM Runner
$Root = ".\LIVE_CRM"
$Venv = "$Root\.venv"

& "$Venv\Scripts\Activate.ps1"
$env:PYTHONPATH = "$Root"

Write-Host "Starting ABUZ8 LIVE CRM on http://localhost:8765 ..." -ForegroundColor Green
Start-Process "http://localhost:8765"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
