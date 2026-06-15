# ABUZ8 CRM Task Scheduler Setup
# Prints exactly what will be created; does not create without confirmation.

$Root = ".\LIVE_CRM"
$Venv = "$Root\.venv"

$tasks = @(
    @{
        Name = "ABUZ8 CRM Monitor"
        Trigger = "Every 5 minutes"
        Action = "powershell.exe -ExecutionPolicy Bypass -File `"$Root\scripts\monitor_now.ps1`""
    },
    @{
        Name = "ABUZ8 CRM Incremental Scan"
        Trigger = "Daily at 06:00"
        Action = "powershell.exe -ExecutionPolicy Bypass -File `"$Root\scripts\scan_now.ps1`""
    },
    @{
        Name = "ABUZ8 CRM Snapshot"
        Trigger = "Daily at 23:00"
        Action = "powershell.exe -ExecutionPolicy Bypass -Command `"& '$Venv\Scripts\Activate.ps1'; \$env:PYTHONPATH='$Root'; python -c 'from app.snapshot import create_snapshot; create_snapshot()'`""
    }
)

Write-Host "The following scheduled tasks will be created:" -ForegroundColor Yellow
foreach ($t in $tasks) {
    Write-Host "  - $($t.Name): $($t.Trigger) => $($t.Action)"
}

$confirm = Read-Host "Create these tasks? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Aborted." -ForegroundColor Red
    exit
}

foreach ($t in $tasks) {
    # Remove existing if present
    schtasks /Delete /TN $t.Name /F 2>$null
    if ($t.Trigger -like "Every*") {
        $minutes = [regex]::Match($t.Trigger, '\d+').Value
        schtasks /Create /TN $t.Name /TR $t.Action /SC MINUTE /MO $minutes /RU SYSTEM /RL HIGHEST /F
    } else {
        schtasks /Create /TN $t.Name /TR $t.Action /SC DAILY /ST 06:00 /RU SYSTEM /RL HIGHEST /F
    }
    Write-Host "Created: $($t.Name)" -ForegroundColor Green
}

Write-Host "Scheduled tasks created." -ForegroundColor Green
