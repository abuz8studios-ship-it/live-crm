"""Realistic valuation engine for ABUZ8 CRM"""
import re
from datetime import datetime, timezone
from pathlib import Path
from .db import get_conn
from .settings import REPORTS_DIR


def compute_valuation(project: dict) -> dict:
    notes = (project.get("notes") or "").lower()
    name = (project.get("name") or "").lower()
    status = (project.get("status") or "").lower()
    completion = project.get("completion_pct", 0) or 0
    category = (project.get("category") or "").lower()

    # Verified market value
    arr = 0.0
    mrr = 0.0
    for m in re.finditer(r"arr[:\s]*\$?([0-9,.]+)([kmb]?)", notes):
        val = parse_money(m.group(1), m.group(2))
        if val:
            arr = val
    for m in re.finditer(r"mrr[:\s]*\$?([0-9,.]+)([kmb]?)", notes):
        val = parse_money(m.group(1), m.group(2))
        if val:
            mrr = val

    verified = 0.0
    if arr > 0:
        verified = arr * 2.0
    elif mrr > 0:
        verified = mrr * 12 * 2.0
    elif "paying customer" in notes or "contract" in notes or "invoice" in notes:
        verified = 500.0

    # Replacement cost
    hours = completion * 2.5
    rate = 75.0
    if "production" in notes or "deployed" in notes:
        rate = 150.0
    elif "internal tool" in notes or "script" in notes:
        rate = 100.0

    usefulness = 0.6
    if completion < 30:
        usefulness = 0.2
    elif completion >= 80:
        usefulness = 0.9

    replacement = hours * rate * usefulness

    # Strategic upside
    upside = 0.0
    if completion >= 70 and ("market" in notes or "customer" in notes or "demo" in notes):
        upside = replacement * 1.5
    elif completion >= 40:
        upside = replacement * 0.5

    # Confidence
    confidence = 10
    if arr > 0 or mrr > 0:
        confidence = 80
    elif verified > 0:
        confidence = 60
    elif completion >= 80 and ("demo" in notes or "deployed" in notes):
        confidence = 50
    elif completion >= 50:
        confidence = 30

    method = "Heuristic: ARR/MRR extraction + replacement hours + strategic multiplier"
    evidence = f"completion={completion}%, notes_length={len(notes)}"
    if arr > 0:
        evidence += f", ARR=${arr:,.0f}"
    if mrr > 0:
        evidence += f", MRR=${mrr:,.0f}"

    proof_needed = "Revenue proof (invoices, stripe data, user metrics) required to increase confidence."
    if verified == 0:
        proof_needed += " Currently no verified revenue."

    # Surgical next monetization action
    next_action = project.get("next_action") or ""
    if not next_action:
        if completion < 25:
            next_action = "Define MVP scope and build first working version."
        elif completion < 60:
            next_action = "Complete core features and create demo recording."
        elif completion < 85:
            next_action = "Deploy to live environment and get first user feedback."
        else:
            next_action = "Pitch to 5 potential buyers or publish for revenue."

    # To reach 100%
    to_100 = []
    if completion < 100:
        if "dashboard" in name or "crm" in name:
            to_100 = ["Finish all API endpoints", "Build remaining dashboard tabs", "Add user auth", "Test end-to-end", "Deploy"]
        elif "comfy" in name or "video" in name:
            to_100 = ["Fix broken nodes", "Complete test renders", "Hit production target", "Review quality", "Upload"]
        elif "agent" in name or "brain" in name:
            to_100 = ["Add remaining tools", "Test with real tasks", "Add error recovery", "Document usage"]
        elif "website" in name:
            to_100 = ["Finish all pages", "Add forms", "Set up hosting", "Add analytics", "Go live"]
        elif "youtube" in name:
            to_100 = ["Create channel", "Produce 5 videos", "Design thumbnails", "Publish first batch"]
        else:
            to_100 = ["Complete build", "Test thoroughly", "Get user feedback", "Iterate", "Launch"]

    return {
        "verified_market_value": round(verified, 2),
        "replacement_cost_value": round(replacement, 2),
        "strategic_upside_value": round(upside, 2),
        "valuation_confidence": confidence,
        "valuation_method": method,
        "evidence": evidence,
        "proof_needed": proof_needed,
        "next_monetization_action": next_action,
        "steps_to_100": to_100,
    }


def parse_money(num_str: str, suffix: str) -> float:
    try:
        val = float(num_str.replace(",", ""))
        s = suffix.lower()
        if s == "k":
            val *= 1000
        elif s == "m":
            val *= 1_000_000
        elif s == "b":
            val *= 1_000_000_000
        return val
    except Exception:
        return 0.0


def run_valuation():
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    with get_conn() as conn:
        for row in conn.execute("SELECT * FROM projects WHERE status != 'Graveyard'"):
            proj = dict(row)
            val = compute_valuation(proj)
            conn.execute(
                """UPDATE projects SET
                market_value_verified=?,
                replacement_cost_value=?,
                strategic_upside_value=?,
                valuation_confidence=?,
                valuation_method=?,
                next_action=?,
                updated_at=?
                WHERE id=?""",
                (
                    val["verified_market_value"],
                    val["replacement_cost_value"],
                    val["strategic_upside_value"],
                    val["valuation_confidence"],
                    val["valuation_method"],
                    val["next_monetization_action"],
                    now,
                    proj["id"],
                ),
            )
            rows.append({**proj, **val})
        conn.commit()

    md = "# ABUZ8 Valuation Report\n\n"
    md += f"Generated: {now}\n\n"
    md += "| Project | Verified $ | Replacement $ | Strategic $ | Conf | Steps to 100% |\n"
    md += "|---|---|---|---|---|---|\n"
    for r in rows:
        steps = ", ".join(r.get("steps_to_100", [])[:3]) if r.get("steps_to_100") else "—"
        md += f"| {r['name']} | ${r['verified_market_value']:,.0f} | ${r['replacement_cost_value']:,.0f} | ${r['strategic_upside_value']:,.0f} | {r['valuation_confidence']}% | {steps} |\n"

    md += "\n## Detailed Project Valuations\n\n"
    for r in rows:
        md += f"### {r['name']}\n"
        md += f"- **Status:** {r['status']} | **Completion:** {r['completion_pct']}%\n"
        md += f"- **Verified Market Value:** ${r['verified_market_value']:,.0f}\n"
        md += f"- **Replacement Cost:** ${r['replacement_cost_value']:,.0f}\n"
        md += f"- **Strategic Upside (SPECULATIVE):** ${r['strategic_upside_value']:,.0f}\n"
        md += f"- **Confidence:** {r['valuation_confidence']}%\n"
        md += f"- **Evidence:** {r['evidence']}\n"
        md += f"- **Proof Needed:** {r['proof_needed']}\n"
        md += f"- **Next Monetization Action:** {r['next_monetization_action']}\n"
        if r.get("steps_to_100"):
            md += "- **Steps to 100%:**\n"
            for s in r["steps_to_100"]:
                md += f"  - {s}\n"
        md += "\n"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "valuation_report.md").write_text(md, encoding="utf-8")
    return rows
