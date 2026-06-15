# ABUZ8 LIVE CRM

Persistent live CRM for the owner / ABUZ8.

## Quick Start

```powershell
# Install
cd .\LIVE_CRM
.\scripts\install_crm.ps1

# Run
cd .\LIVE_CRM
.\scripts\run_crm.ps1
```

Dashboard opens at http://localhost:8765

## Manual Operations

- **Scan now**: `.\scripts\scan_now.ps1`
- **Monitor now**: `.\scripts\monitor_now.ps1`
- **Scheduled tasks**: `.\scripts\create_task_scheduler.ps1`

## Structure

- `app/` — FastAPI backend, scanners, monitors, engines
- `web/` — Dashboard HTML/JS/CSS
- `data/` — SQLite DB, snapshots, exports
- `scripts/` — PowerShell automation
- `reports/` — Markdown reports

## Tech Stack

- FastAPI + Uvicorn
- SQLite (persistent)
- Vanilla JS dashboard
- psutil + nvidia-smi
- PowerShell automation
