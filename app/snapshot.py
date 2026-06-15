"""Snapshot system for ABUZ8 CRM"""
import shutil
import json
from datetime import datetime, timezone
from pathlib import Path
from .settings import DB_PATH, SNAPSHOTS_DIR, REPORTS_DIR
from .db import get_conn


def create_snapshot(snapshot_type: str = "daily") -> dict:
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%d")
    snap_dir = SNAPSHOTS_DIR / ts
    snap_dir.mkdir(parents=True, exist_ok=True)

    # Backup DB
    db_backup = snap_dir / "abu_crm.sqlite.bak"
    shutil.copy2(str(DB_PATH), str(db_backup))

    # Copy reports if they exist
    for report_name in [
        "revenue_today.md",
        "valuation_report.md",
        "system_health.md",
        "context_card.md",
    ]:
        src = REPORTS_DIR / report_name
        if src.exists():
            shutil.copy2(str(src), str(snap_dir / report_name))

    summary = f"Snapshot {snapshot_type} at {now.isoformat()}. DB backup + reports."
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO snapshots (timestamp, snapshot_type, path, summary) VALUES (?,?,?,?)",
            (now.isoformat(), snapshot_type, str(snap_dir), summary),
        )
        conn.commit()

    return {
        "timestamp": now.isoformat(),
        "type": snapshot_type,
        "path": str(snap_dir),
        "summary": summary,
    }
