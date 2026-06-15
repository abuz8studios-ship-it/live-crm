# ABUZ8 CRM Monitor Now
$Root = ".\LIVE_CRM"
$Venv = "$Root\.venv"
& "$Venv\Scripts\Activate.ps1"
$env:PYTHONPATH = "$Root"

Write-Host "=== System Monitor ===" -ForegroundColor Cyan
python -c "from app.monitor_system import capture_system_metrics; print(capture_system_metrics())"
Write-Host "=== Agent Monitor ===" -ForegroundColor Cyan
python -c "from app.monitor_agents import discover_agents; print(discover_agents())"
Write-Host "=== Comfy Tracker ===" -ForegroundColor Cyan
python -c "from app.comfy_tracker import sync_comfy_jobs; print(sync_comfy_jobs())"
Write-Host "=== Monitor complete ===" -ForegroundColor Green
