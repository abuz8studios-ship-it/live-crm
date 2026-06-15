"""ABUZ8 LIVE CRM FastAPI Backend"""
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db
from . import scanner_files
from . import scanner_models
from . import scanner_programs
from . import monitor_system
from . import monitor_agents
from . import valuation
from . import revenue_engine
from . import comfy_tracker
from . import context_card
from . import snapshot
from . import workflows
from .settings import CRM_ROOT, WEB_DIR, REPORTS_DIR, DATA_DIR

app = FastAPI(title="ABUZ8 LIVE CRM")

# Static files
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


def rows_to_list(rows):
    return [dict(r) for r in rows]


@app.get("/")
def serve_dashboard():
    index = WEB_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"message": "Dashboard not built yet."})


@app.get("/api/summary")
def api_summary():
    with db.get_conn() as conn:
        proj_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        file_count = conn.execute("SELECT COUNT(*) FROM files WHERE status != 'Archived'").fetchone()[0]
        model_count = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
        prog_count = conn.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
        agent_count = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        active_agent_count = conn.execute("SELECT COUNT(*) FROM agents WHERE status IN ('LIVE','IDLE')").fetchone()[0]
        latest_scan = conn.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 1").fetchone()
        latest_mon = conn.execute("SELECT * FROM system_metrics ORDER BY id DESC LIMIT 1").fetchone()
        top_proj = conn.execute("SELECT * FROM projects WHERE status != 'Graveyard' ORDER BY today_score DESC LIMIT 1").fetchone()
        top_act = conn.execute("SELECT * FROM actions WHERE status='auto' ORDER BY eta_hours LIMIT 1").fetchone()
    return {
        "project_count": proj_count,
        "file_count": file_count,
        "model_count": model_count,
        "program_count": prog_count,
        "agent_count": agent_count,
        "active_agent_count": active_agent_count,
        "latest_scan": dict(latest_scan) if latest_scan else None,
        "latest_monitor": dict(latest_mon) if latest_mon else None,
        "top_project": dict(top_proj) if top_proj else None,
        "top_action": dict(top_act) if top_act else None,
    }


@app.get("/api/projects")
def api_projects(status: Optional[str] = Query(None), sort: Optional[str] = Query("today_score")):
    with db.get_conn() as conn:
        sql = "SELECT * FROM projects"
        params = []
        if status:
            sql += " WHERE status=?"
            params.append(status)
        order = "today_score DESC" if sort == "today_score" else "updated_at DESC"
        sql += f" ORDER BY {order}"
        rows = conn.execute(sql, params).fetchall()
    return rows_to_list(rows)


@app.get("/api/files")
def api_files(q: Optional[str] = Query(None), status: Optional[str] = Query(None)):
    with db.get_conn() as conn:
        sql = "SELECT * FROM files WHERE 1=1"
        params = []
        if status:
            sql += " AND status=?"
            params.append(status)
        if q:
            sql += " AND (path LIKE ? OR filename LIKE ? OR summary LIKE ?)"
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
        sql += " ORDER BY last_scanned_at DESC LIMIT 2000"
        rows = conn.execute(sql, params).fetchall()
    return rows_to_list(rows)


@app.get("/api/models")
def api_models():
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM models ORDER BY size_bytes DESC LIMIT 1000").fetchall()
    return rows_to_list(rows)


@app.get("/api/programs")
def api_programs():
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM programs ORDER BY category").fetchall()
    return rows_to_list(rows)


@app.get("/api/agents")
def api_agents():
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM agents ORDER BY status").fetchall()
    return rows_to_list(rows)


@app.get("/api/system")
def api_system():
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM system_metrics ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else {}


@app.get("/api/actions")
def api_actions():
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM actions ORDER BY created_at DESC LIMIT 200").fetchall()
    return rows_to_list(rows)


@app.get("/api/comfy")
def api_comfy():
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM comfy_jobs").fetchall()
    return rows_to_list(rows)


@app.get("/api/context-card")
def api_context_card():
    text = context_card.generate_context_card()
    return {"content": text}


@app.get("/api/revenue-today")
def api_revenue_today():
    path = REPORTS_DIR / "revenue_today.md"
    if path.exists():
        return {"content": path.read_text(encoding="utf-8")}
    return {"content": "Not generated yet."}


@app.get("/api/valuation")
def api_valuation():
    path = REPORTS_DIR / "valuation_report.md"
    if path.exists():
        return {"content": path.read_text(encoding="utf-8")}
    return {"content": "Not generated yet."}


@app.post("/api/scan")
def api_scan():
    try:
        res_files = scanner_files.scan_files_incremental()
    except Exception as e:
        res_files = {"error": str(e)}
    try:
        res_models = scanner_models.scan_models()
    except Exception as e:
        res_models = {"error": str(e)}
    try:
        res_progs = scanner_programs.scan_programs()
    except Exception as e:
        res_progs = {"error": str(e)}
    try:
        revenue_engine.run_revenue_engine()
    except Exception as e:
        pass
    try:
        context_card.generate_context_card()
    except Exception:
        pass
    try:
        workflows.ensure_checklists()
    except Exception:
        pass
    return {"files": res_files, "models": res_models, "programs": res_progs}


@app.post("/api/monitor")
def api_monitor():
    try:
        sys_data = monitor_system.capture_system_metrics()
    except Exception as e:
        sys_data = {"error": str(e)}
    try:
        agents = monitor_agents.discover_agents()
    except Exception as e:
        agents = {"error": str(e)}
    try:
        comfy_tracker.sync_comfy_jobs()
    except Exception:
        pass
    return {"system": sys_data, "agents": agents}


@app.post("/api/project/update")
def api_project_update(project_id: int, status: Optional[str] = None, completion_pct: Optional[int] = None, next_action: Optional[str] = None, blocker: Optional[str] = None):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with db.get_conn() as conn:
        sets = []
        params = []
        if status is not None:
            sets.append("status=?")
            params.append(status)
        if completion_pct is not None:
            sets.append("completion_pct=?")
            params.append(completion_pct)
        if next_action is not None:
            sets.append("next_action=?")
            params.append(next_action)
        if blocker is not None:
            sets.append("blocker=?")
            params.append(blocker)
        sets.append("updated_at=?")
        params.append(now)
        params.append(project_id)
        conn.execute(f"UPDATE projects SET {','.join(sets)} WHERE id=?", params)
        conn.commit()
    return {"ok": True}


@app.post("/api/action/update")
def api_action_update(action_id: int, status: str):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with db.get_conn() as conn:
        extra = ""
        params = [status]
        if status.lower() == "completed":
            extra = ", completed_at=?"
            params.append(now)
        params.append(action_id)
        conn.execute(f"UPDATE actions SET status=?{extra} WHERE id=?", params)
        conn.commit()
    return {"ok": True}


@app.post("/api/comfy/update")
def api_comfy_update(job_id: int, status: Optional[str] = None, completed_video_count: Optional[int] = None, failed_count: Optional[int] = None, notes: Optional[str] = None):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with db.get_conn() as conn:
        sets = []
        params = []
        if status is not None:
            sets.append("status=?")
            params.append(status)
        if completed_video_count is not None:
            sets.append("completed_video_count=?")
            params.append(completed_video_count)
        if failed_count is not None:
            sets.append("failed_count=?")
            params.append(failed_count)
        if notes is not None:
            sets.append("notes=?")
            params.append(notes)
        sets.append("last_run_at=?")
        params.append(now)
        params.append(job_id)
        conn.execute(f"UPDATE comfy_jobs SET {','.join(sets)} WHERE id=?", params)
        conn.commit()
    return {"ok": True}


@app.get("/api/export/json")
def api_export_json():
    data = {}
    with db.get_conn() as conn:
        for table in ["projects", "files", "models", "programs", "agents", "system_metrics", "scans", "actions", "comfy_jobs", "snapshots"]:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            data[table] = rows_to_list(rows)
    export_path = DATA_DIR / "exports" / "crm_export.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return FileResponse(str(export_path), filename="crm_export.json")


@app.get("/api/export/context")
def api_export_context():
    text = context_card.generate_context_card()
    export_path = DATA_DIR / "exports" / "context_card.md"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")
    return FileResponse(str(export_path), filename="context_card.md")


@app.get("/api/project/{project_id}/workflow")
def api_project_workflow(project_id: int):
    data = workflows.get_project_workflow(project_id)
    if not data:
        return JSONResponse({"error": "Project not found"}, status_code=404)
    return data


@app.post("/api/project/{project_id}/checklist/{step_number}")
def api_update_checklist(project_id: int, step_number: int, is_done: int):
    result = workflows.update_checklist_item(project_id, step_number, is_done)
    return result


@app.get("/api/export/report")
def api_export_report():
    import zipfile
    zip_path = DATA_DIR / "exports" / "reports.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for f in REPORTS_DIR.glob("*.md"):
            zf.write(str(f), arcname=f.name)
    return FileResponse(str(zip_path), filename="reports.zip")
