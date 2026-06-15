"""Project workflow engine — generates surgical completion roadmaps"""
from datetime import datetime, timezone
from .db import get_conn


def generate_checklist(project: dict) -> list:
    """Generate a surgical checklist based on project type and current completion."""
    name = (project.get("name") or "").lower()
    category = (project.get("category") or "").lower()
    completion = project.get("completion_pct", 0) or 0
    steps = []

    # Base steps by category
    if "dashboard" in name or "crm" in name:
        steps = [
            ("Define all required tables and schema", 2, "Database design"),
            ("Build backend API endpoints", 4, "FastAPI routes"),
            ("Build frontend dashboard UI", 4, "HTML/CSS/JS"),
            ("Connect frontend to backend APIs", 2, "Integration"),
            ("Add authentication / access control", 3, "Security"),
            ("Test all endpoints with real data", 2, "QA"),
            ("Deploy and document usage", 2, "Deployment"),
        ]
    elif "comfy" in name or "video" in name or "media" in name:
        steps = [
            ("Confirm working ComfyUI installation", 1, "Infrastructure"),
            ("Test all required custom_nodes", 2, "Node validation"),
            ("Build or import base workflow", 2, "Workflow"),
            ("Create prompt templates", 2, "Prompts"),
            ("Run test renders (10 images)", 2, "Testing"),
            ("Fix broken nodes / missing models", 3, "Debugging"),
            ("Batch render target output (50 videos)", 8, "Production"),
            ("Review outputs for quality", 2, "QA"),
            ("Upload to YouTube / delivery", 2, "Delivery"),
        ]
    elif "agent" in name or "brain" in name or "mcp" in name:
        steps = [
            ("Define agent scope and boundaries", 2, "Architecture"),
            ("Set up framework (OpenClaw / Hermes / etc)", 2, "Setup"),
            ("Build core logic / prompt chain", 3, "Core"),
            ("Add tool integrations (MCP, browser, etc)", 4, "Tools"),
            ("Test with real tasks", 3, "Testing"),
            ("Add error handling and recovery", 2, "Hardening"),
            ("Document usage and limits", 1, "Docs"),
        ]
    elif "website" in name or "abuz8ai" in name:
        steps = [
            ("Register domain and verify DNS", 1, "Domain"),
            ("Design page structure", 2, "Design"),
            ("Build landing page", 3, "Frontend"),
            ("Add contact / CTA forms", 2, "Forms"),
            ("Set up hosting / CDN", 2, "Hosting"),
            ("Add analytics", 1, "Analytics"),
            ("Go live and test", 1, "Launch"),
        ]
    elif "voice" in name or "rvc" in name or "tts" in name:
        steps = [
            ("Install voice pipeline dependencies", 2, "Setup"),
            ("Source training audio (clean, 10+ min)", 2, "Data"),
            ("Train RVC model", 4, "Training"),
            ("Test inference quality", 2, "Testing"),
            ("Integrate with production pipeline", 2, "Integration"),
        ]
    elif "pdf" in name or "extractor" in name or "knowledge" in name:
        steps = [
            ("Define input formats (PDF, DOCX, etc)", 1, "Scope"),
            ("Set up parsing pipeline", 2, "Parser"),
            ("Add OCR for scanned pages", 2, "OCR"),
            ("Build chunking and embedding logic", 3, "RAG"),
            ("Connect to vector DB", 2, "Storage"),
            ("Build query interface", 2, "UI"),
            ("Test with real documents", 2, "QA"),
        ]
    elif "youtube" in name:
        steps = [
            ("Create YouTube channel / brand", 1, "Setup"),
            ("Define content strategy and schedule", 2, "Strategy"),
            ("Produce first 5 videos", 5, "Production"),
            ("Design thumbnails and titles", 2, "Branding"),
            ("Set up upload pipeline", 1, "Automation"),
            ("Publish and promote first batch", 2, "Launch"),
        ]
    elif "avatar" in name:
        steps = [
            ("Define avatar style guide", 2, "Design"),
            ("Build consistency pipeline", 3, "Pipeline"),
            ("Generate base avatar set (10 poses)", 3, "Generation"),
            ("Test consistency across renders", 2, "QA"),
            ("Package for production use", 2, "Delivery"),
        ]
    elif "lotvue" in name or "360" in name:
        steps = [
            ("Define product spec and user flow", 2, "Spec"),
            ("Build 360 viewer component", 3, "Frontend"),
            ("Add image/video hotspot logic", 2, "Features"),
            ("Test on mobile and desktop", 2, "QA"),
            ("Find first beta customer", 2, "Sales"),
        ]
    elif "linkedin" in name:
        steps = [
            ("Define service offering and pricing", 2, "Pricing"),
            ("Build audit checklist template", 2, "Template"),
            ("Create outreach message sequence", 2, "Outreach"),
            ("Send first 20 outreach messages", 2, "Sales"),
            ("Close first paying client", 3, "Revenue"),
        ]
    elif "pm" in name or "workflow" in name or "rescue" in name:
        steps = [
            ("Map current broken workflow", 2, "Audit"),
            ("Identify automation opportunities", 2, "Analysis"),
            ("Build automation scripts", 4, "Build"),
            ("Test with real project data", 2, "QA"),
            ("Document new workflow", 1, "Docs"),
            ("Pitch to first client", 2, "Sales"),
        ]
    else:
        steps = [
            ("Define exact scope and deliverable", 2, "Scope"),
            ("Build minimum viable version", 4, "Build"),
            ("Test with realistic data", 2, "QA"),
            ("Get feedback from one user", 2, "Validation"),
            ("Iterate based on feedback", 2, "Iterate"),
            ("Document and package", 1, "Docs"),
            ("Attempt first sale or deployment", 2, "Launch"),
        ]

    # Calculate which steps are done based on completion %
    total_steps = len(steps)
    done_count = int((completion / 100.0) * total_steps)

    checklist = []
    for i, (desc, eta, tag) in enumerate(steps, 1):
        checklist.append({
            "step_number": i,
            "description": desc,
            "eta_hours": eta,
            "is_done": 1 if i <= done_count else 0,
            "money_path": tag,
            "required_agent": project.get("assigned_agent") or "Unassigned",
        })

    return checklist


def ensure_checklists():
    """Generate checklists for all projects that don't have one."""
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        projects = conn.execute("SELECT * FROM projects").fetchall()
        for proj in projects:
            pid = proj["id"]
            existing = conn.execute("SELECT COUNT(*) FROM project_checklists WHERE project_id=?", (pid,)).fetchone()[0]
            if existing > 0:
                continue
            checklist = generate_checklist(dict(proj))
            for item in checklist:
                conn.execute(
                    """INSERT INTO project_checklists
                    (project_id, step_number, description, eta_hours, is_done, money_path, required_agent, created_at)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (pid, item["step_number"], item["description"], item["eta_hours"], item["is_done"], item["money_path"], item["required_agent"], now)
                )
        conn.commit()


def get_project_workflow(project_id: int) -> dict:
    """Get full workflow data for a project."""
    with get_conn() as conn:
        proj = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not proj:
            return None
        proj = dict(proj)
        checklist = [dict(r) for r in conn.execute("SELECT * FROM project_checklists WHERE project_id=? ORDER BY step_number", (project_id,))]
        files = [dict(r) for r in conn.execute("SELECT * FROM files WHERE project_id=? OR path LIKE ? ORDER BY modified_at DESC LIMIT 20", (project_id, f"%{proj['name']}%"))]
    return {
        "project": proj,
        "checklist": checklist,
        "files": files,
        "next_uncheck": next((c for c in checklist if not c["is_done"]), None),
        "total_eta": sum(c["eta_hours"] for c in checklist if not c["is_done"]),
    }


def update_checklist_item(project_id: int, step_number: int, is_done: int) -> dict:
    """Update a checklist item and recalculate project completion."""
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE project_checklists SET is_done=? WHERE project_id=? AND step_number=?",
            (is_done, project_id, step_number)
        )
        # Recalculate completion
        total = conn.execute("SELECT COUNT(*) FROM project_checklists WHERE project_id=?", (project_id,)).fetchone()[0]
        done = conn.execute("SELECT COUNT(*) FROM project_checklists WHERE project_id=? AND is_done=1", (project_id,)).fetchone()[0]
        new_pct = int((done / max(total, 1)) * 100)
        conn.execute(
            "UPDATE projects SET completion_pct=?, updated_at=? WHERE id=?",
            (new_pct, now, project_id)
        )
        conn.commit()
        return {"completion_pct": new_pct, "done": done, "total": total}
