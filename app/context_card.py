"""Universal context card generator for ABUZ8 CRM"""
from datetime import datetime, timezone
from .db import get_conn
from .settings import REPORTS_DIR


def generate_context_card():
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        active_projects = [dict(r) for r in conn.execute("SELECT * FROM projects WHERE status IN ('Active','Needs Review') ORDER BY today_score DESC LIMIT 10")]
        completed_projects = [dict(r) for r in conn.execute("SELECT * FROM projects WHERE status='Complete' LIMIT 5")]
        graveyard = [dict(r) for r in conn.execute("SELECT * FROM projects WHERE status IN ('Graveyard','Killed') LIMIT 5")]
        agents = [dict(r) for r in conn.execute("SELECT * FROM agents ORDER BY status")]
        models = [dict(r) for r in conn.execute("SELECT * FROM models LIMIT 10")]
        actions = [dict(r) for r in conn.execute("SELECT * FROM actions WHERE status='auto' ORDER BY eta_hours LIMIT 5")]
        comfy = [dict(r) for r in conn.execute("SELECT * FROM comfy_jobs LIMIT 5")]
        latest_sys = conn.execute("SELECT * FROM system_metrics ORDER BY id DESC LIMIT 1").fetchone()

    card = "=== ABUZ8 UNIVERSAL AI CONTEXT CARD ===\n"
    card += f"OWNER: the owner / ABUZ8\n"
    card += f"GENERATED: {now}\n\n"

    card += "MACHINE SUMMARY:\n"
    if latest_sys:
        card += f"- CPU: {latest_sys['cpu_pct']}%, RAM: {latest_sys['ram_used_gb']}/{latest_sys['ram_total_gb']} GB\n"
        card += f"- GPU0: {latest_sys['gpu0_name'] or 'None'} {latest_sys['gpu0_util_pct']}% VRAM {latest_sys['gpu0_vram_used_gb']}/{latest_sys['gpu0_vram_total_gb']} GB\n"
        card += f"- GPU1: {latest_sys['gpu1_name'] or 'None'} {latest_sys['gpu1_util_pct']}% VRAM {latest_sys['gpu1_vram_used_gb']}/{latest_sys['gpu1_vram_total_gb']} GB\n"
    else:
        card += "- No system metrics yet.\n"

    card += "\nACTIVE AGENTS:\n"
    for a in agents:
        card += f"- {a['name']} [{a['status']}] {a['framework']} {a['current_task'] or ''}\n"

    card += "\nACTIVE PROJECTS:\n"
    for p in active_projects:
        card += f"- {p['name']} ({p['status']}) completion={p['completion_pct']}% score={p['today_score']} agent={p['assigned_agent'] or 'none'}\n"

    card += "\nCOMPLETED PROJECTS:\n"
    for p in completed_projects:
        card += f"- {p['name']}\n"

    card += "\nKILLED / DO NOT REVISIT:\n"
    for p in graveyard:
        card += f"- {p['name']}: {p['notes'][:80]}\n"

    card += "\nTECH STACK:\n"
    card += "- FastAPI + SQLite + vanilla JS dashboard\n"
    card += "- Windows + Python + PowerShell automation\n"
    card += "- ComfyUI + Ollama + Open WebUI + LM Studio\n"

    card += "\nAI MODEL STACK:\n"
    for m in models[:5]:
        card += f"- {m['name']} ({m['model_type']}) {m['architecture']}\n"

    card += "\nCOMFYUI STATUS:\n"
    for c in comfy:
        card += f"- {c['name']}: {c['completed_video_count']}/{c['target_video_count']} videos, status={c['status']}\n"

    card += "\nREVENUE PIPELINE:\n"
    for a in actions:
        card += f"- {a['action']} (agent={a['assigned_agent']}, eta={a['eta_hours']}h)\n"

    card += "\nCURRENT BLOCKERS:\n"
    blockers = [p for p in active_projects if p.get("blocker")]
    if blockers:
        for p in blockers[:3]:
            card += f"- {p['name']}: {p['blocker']}\n"
    else:
        card += "- None recorded.\n"

    card += "\nTOP ACTION TODAY:\n"
    if actions:
        card += f"{actions[0]['action']}\n"
    elif active_projects:
        card += f"Work on {active_projects[0]['name']}: {active_projects[0].get('next_action') or 'Define next step'}\n"
    else:
        card += "Define a revenue project and assign an agent.\n"

    card += "\nDO NOT REPEAT:\n"
    card += "- Do not rebuild CRM from scratch; iterate this dashboard.\n"
    card += "- Do not restart abandoned projects without revenue proof.\n"
    card += "- Do not expose secrets in any output.\n"

    card += "\nCONTINUE FROM HERE:\n"
    if actions:
        card += f"Execute action: {actions[0]['action']}\n"
    else:
        card += "Run scan_now.ps1 to populate data, then pick highest-score project.\n"

    card += "\n=== END CONTEXT CARD ===\n"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "context_card.md").write_text(card, encoding="utf-8")
    return card
