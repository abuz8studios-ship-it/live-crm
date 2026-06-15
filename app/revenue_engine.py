"""Revenue action engine for ABUZ8 CRM"""
import math
from datetime import datetime, timezone
from .db import get_conn
from .settings import REPORTS_DIR


def compute_today_score(project: dict) -> float:
    completion = max(1, project.get("completion_pct", 0) or 0)
    feasibility = max(1, project.get("urf_feasibility", 5) or 5)
    urgency = max(1, project.get("urf_urgency", 5) or 5)
    hours = max(1, project.get("next_action_eta_hours", 999) or 999)
    blocker = project.get("blocker") or ""
    blocker_penalty = 50 if blocker else 0
    status = project.get("status", "").lower()
    if status in ("abandoned", "broken", "archived"):
        return 0.0
    revenue_probability = min(1.0, completion / 100.0)
    score = (completion * feasibility * revenue_probability * urgency) / (hours + blocker_penalty)
    return round(score, 2)


def run_revenue_engine():
    now = datetime.now(timezone.utc).isoformat()
    projects = []
    with get_conn() as conn:
        for row in conn.execute("SELECT * FROM projects"):
            proj = dict(row)
            score = compute_today_score(proj)
            conn.execute(
                "UPDATE projects SET today_score=? WHERE id=?",
                (score, proj["id"]),
            )
            proj["today_score"] = score
            projects.append(proj)
        conn.commit()

    active = [p for p in projects if p["status"].lower() not in ("graveyard", "killed", "archived", "abandoned")]
    active.sort(key=lambda x: x["today_score"], reverse=True)

    graveyard = [p for p in projects if p["status"].lower() in ("graveyard", "killed")]

    top_3 = active[:3]
    ship_24h = [p for p in active if (p.get("completion_pct") or 0) >= 70 and p.get("next_action_eta_hours", 999) <= 8][:3]
    ship_48h = [p for p in active if (p.get("completion_pct") or 0) >= 50 and p.get("next_action_eta_hours", 999) <= 24][:3]
    freeze = [p for p in active if (p.get("blocker") or "") != ""][:3]
    kill = [p for p in active if (p.get("completion_pct") or 0) < 15 and (p.get("evidence_score") or 0) < 10][:3]

    # Build actions table
    with get_conn() as conn:
        conn.execute("DELETE FROM actions WHERE status='auto'")
        for i, p in enumerate(top_3):
            conn.execute(
                """INSERT INTO actions (project_id, action, reason, eta_hours, money_unlocked, status, due_date, created_at, assigned_agent)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    p["id"],
                    p.get("next_action") or "Define next step",
                    f"Top revenue priority #{i+1} based on TODAY_SCORE",
                    p.get("next_action_eta_hours", 999),
                    p.get("revenue_potential", 0),
                    "auto",
                    now[:10],
                    now,
                    p.get("assigned_agent") or "Unassigned",
                ),
            )
        conn.commit()

    md = "# Revenue Today — ABUZ8\n\n"
    md += f"Generated: {now}\n\n"

    md += "## Top 3 Actions to Make Money Today\n\n"
    for p in top_3:
        md += f"- **{p['name']}** (score {p['today_score']})\n"
        md += f"  - Next: {p.get('next_action') or 'TBD'}\n"
        md += f"  - ETA: {p.get('next_action_eta_hours', 999)}h | Agent: {p.get('assigned_agent') or 'Unassigned'}\n\n"

    md += "## Top 3 Assets to Finish in 24 Hours\n\n"
    for p in ship_24h:
        md += f"- **{p['name']}** — {p.get('next_action') or 'Ship it'}\n"

    md += "\n## Top 3 Assets to Package/Post in 48 Hours\n\n"
    for p in ship_48h:
        md += f"- **{p['name']}** — {p.get('next_action') or 'Package and post'}\n"

    md += "\n## Projects to Freeze\n\n"
    for p in freeze:
        md += f"- **{p['name']}** — Blocker: {p.get('blocker')}\n"

    md += "\n## Projects to Kill\n\n"
    for p in kill:
        md += f"- **{p['name']}** — Low completion ({p.get('completion_pct')}%) and no evidence.\n"

    md += "\n## One Active Battlefield Recommendation\n\n"
    if top_3:
        rec = top_3[0]
        md += f"Focus on **{rec['name']}**. It has the highest TODAY_SCORE ({rec['today_score']}). "
        md += f"Action: {rec.get('next_action') or 'Define exact deliverable and ship today.'}\n"
    else:
        md += "No active projects scored. Define a small deliverable with revenue path and assign an agent.\n"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "revenue_today.md").write_text(md, encoding="utf-8")
    return {
        "top_3": top_3,
        "ship_24h": ship_24h,
        "ship_48h": ship_48h,
        "freeze": freeze,
        "kill": kill,
    }
