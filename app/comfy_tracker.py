"""ComfyUI production tracker for ABUZ8 CRM"""
import json
from datetime import datetime, timezone
from pathlib import Path
from .db import get_conn
from .settings import REPORTS_DIR


def discover_comfy_jobs():
    """Auto-discover ComfyUI workflows and output folders."""
    jobs = []
    comfy_roots = []
    for root in [Path("~/ComfyUI"), Path("E:/")]:
        if not root.exists():
            continue
        try:
            for p in root.rglob("*"):
                if p.is_dir() and p.name.lower() == "comfyui":
                    comfy_roots.append(p)
        except Exception:
            pass

    for cr in comfy_roots:
        # outputs
        out_dir = cr / "output"
        if out_dir.exists():
            video_count = 0
            image_count = 0
            for f in out_dir.rglob("*"):
                if f.is_file():
                    if f.suffix.lower() in (".mp4", ".mov", ".avi", ".mkv"):
                        video_count += 1
                    if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                        image_count += 1
            jobs.append({
                "name": "ComfyUI Output Folder",
                "workflow_path": str(cr / "workflows"),
                "prompt_path": "",
                "model_used": "",
                "status": "Active",
                "output_path": str(out_dir),
                "target_video_count": 50,
                "completed_video_count": video_count,
                "failed_count": 0,
                "next_render_action": f"Render more videos ({50 - video_count} remaining to hit 50)",
                "last_run_at": datetime.now(timezone.utc).isoformat(),
                "notes": f"Images: {image_count}, Videos: {video_count}",
            })

        # custom nodes health
        custom_nodes = cr / "custom_nodes"
        broken_nodes = []
        if custom_nodes.exists():
            for node_dir in custom_nodes.iterdir():
                if node_dir.is_dir():
                    req = node_dir / "requirements.txt"
                    init = node_dir / "__init__.py"
                    if not init.exists() and not any(node_dir.glob("*.py")):
                        broken_nodes.append(node_dir.name)

        if broken_nodes:
            jobs.append({
                "name": "Broken/Missing Custom Nodes",
                "workflow_path": "",
                "prompt_path": "",
                "model_used": "",
                "status": "Broken",
                "output_path": "",
                "target_video_count": 0,
                "completed_video_count": 0,
                "failed_count": len(broken_nodes),
                "next_render_action": f"Fix or remove nodes: {', '.join(broken_nodes[:5])}",
                "last_run_at": datetime.now(timezone.utc).isoformat(),
                "notes": f"Broken nodes: {broken_nodes}",
            })

    return jobs


def sync_comfy_jobs():
    now = datetime.now(timezone.utc).isoformat()
    jobs = discover_comfy_jobs()
    with get_conn() as conn:
        for j in jobs:
            existing = conn.execute("SELECT id FROM comfy_jobs WHERE name=?", (j["name"],)).fetchone()
            vals = tuple(j.get(k) for k in [
                "name", "workflow_path", "prompt_path", "model_used", "status", "output_path",
                "target_video_count", "completed_video_count", "failed_count",
                "next_render_action", "last_run_at", "notes"
            ])
            if existing:
                conn.execute(
                    """UPDATE comfy_jobs SET workflow_path=?, prompt_path=?, model_used=?, status=?, output_path=?, target_video_count=?, completed_video_count=?, failed_count=?, next_render_action=?, last_run_at=?, notes=? WHERE id=?""",
                    vals[1:] + (existing["id"],),
                )
            else:
                conn.execute(
                    """INSERT INTO comfy_jobs (name, workflow_path, prompt_path, model_used, status, output_path, target_video_count, completed_video_count, failed_count, next_render_action, last_run_at, notes)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    vals,
                )
        conn.commit()

    md = "# ComfyUI Production Status\n\n"
    md += f"Generated: {now}\n\n"
    for j in jobs:
        md += f"## {j['name']}\n"
        md += f"- Status: {j['status']}\n"
        md += f"- Output: {j['output_path']}\n"
        md += f"- Videos: {j['completed_video_count']} / {j['target_video_count']}\n"
        md += f"- Failed: {j['failed_count']}\n"
        md += f"- Next Action: {j['next_render_action']}\n"
        md += f"- Notes: {j['notes']}\n\n"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "comfyui_production_status.md").write_text(md, encoding="utf-8")
    return jobs
