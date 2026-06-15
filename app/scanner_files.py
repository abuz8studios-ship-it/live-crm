"""Incremental file scanner for ABUZ8 CRM"""
import os
import hashlib
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from .db import get_conn
from .settings import SCAN_ROOTS, SAFE_EXTENSIONS, EXCLUDED_DIRS, SECRET_PATTERNS


def should_skip_dir(p: Path) -> bool:
    parts = [part.lower() for part in p.parts]
    for ex in EXCLUDED_DIRS:
        if ex.lower() in parts:
            return True
    return False


def sha256_file(path: Path, max_bytes: int = 1_000_000_000) -> str:
    try:
        size = path.stat().st_size
        if size > max_bytes:
            return f"SIZE:{size}:MTIME:{path.stat().st_mtime}"
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return f"ERROR:{e}"


def guess_category(path: Path, content_hint: str = "") -> str:
    name = path.name.lower()
    parent = str(path.parent).lower()
    if "workflow" in parent or "comfy" in parent:
        return "Workflow"
    if "prompt" in parent:
        return "Prompt"
    if "model" in parent or "checkpoint" in parent or "lora" in parent:
        return "Model"
    if ".md" in name:
        return "Documentation"
    if ".env" in name or "config" in name:
        return "Infrastructure"
    if "test" in name:
        return "Bug Fix"
    if "bug" in name or "fix" in name:
        return "Bug Fix"
    if "agent" in parent or "claude" in parent or "kimi" in parent or "openclaw" in parent:
        return "Agent"
    if any(x in parent for x in ["script", "automation", "tool"]):
        return "Feature"
    if "content" in parent or "youtube" in parent or "video" in parent:
        return "Content"
    if "research" in parent:
        return "Research"
    return "Unknown"


def guess_ai_tool(path: Path) -> str:
    p = str(path).lower()
    if "comfy" in p:
        return "ComfyUI"
    if "openclaw" in p:
        return "OpenClaw"
    if "claude" in p:
        return "Claude Code"
    if "kimi" in p:
        return "Kimi Code"
    if "ollama" in p:
        return "Ollama"
    if "open-webui" in p or "open_webui" in p:
        return "Open WebUI"
    if "lmstudio" in p:
        return "LM Studio"
    if "cursor" in p:
        return "Cursor"
    if "hermes" in p:
        return "Hermes"
    if "agent-zero" in p or "agent_zero" in p:
        return "Agent Zero"
    return "Unknown"


def detect_secrets(text: str) -> list:
    found = []
    for pattern, stype in SECRET_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            found.append({"secret_detected": True, "secret_type": stype, "value_redacted": True})
    return found


def scan_files_incremental():
    now = datetime.now(timezone.utc).isoformat()
    scan_id = None
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO scans (scan_type, started_at, status) VALUES (?,?,?)",
            ("files_incremental", now, "running"),
        )
        scan_id = cur.lastrowid
        conn.commit()

    files_seen = 0
    files_changed = 0
    errors = 0
    new_rows = []
    updated_rows = []
    start_time = time.time()
    MAX_FILES = 25000
    MAX_TIME = 45

    # Load existing files for quick lookup
    existing = {}
    with get_conn() as conn:
        for row in conn.execute("SELECT path, sha256, modified_at, status FROM files"):
            existing[row["path"]] = {
                "sha256": row["sha256"],
                "modified_at": row["modified_at"],
                "status": row["status"],
            }

    seen_paths = set()

    for root_str in SCAN_ROOTS:
        root = Path(root_str)
        if not root.exists():
            continue
        try:
            for p in root.rglob("*"):
                if time.time() - start_time > MAX_TIME or files_seen >= MAX_FILES:
                    break
                if p.is_dir():
                    if should_skip_dir(p):
                        continue
                    continue
                if not p.is_file():
                    continue
                if p.suffix.lower() not in SAFE_EXTENSIONS and not p.name.lower().endswith(".env.example"):
                    if p.name.lower() not in (".env", ".env.local", ".env.production"):
                        continue
                try:
                    files_seen += 1
                    spath = str(p.resolve())
                    seen_paths.add(spath)
                    stat = p.stat()
                    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                    size = stat.st_size
                    ext = p.suffix.lower()
                    sha = sha256_file(p)

                    secret_detected = 0
                    summary = ""
                    unreadable = ""
                    if size < 5_000_000 and p.suffix.lower() in (".txt", ".md", ".py", ".js", ".json", ".yaml", ".yml", ".ps1", ".sh", ".css", ".html", ".csv", ".xml", ".sql", ".env", ".env.local", ".env.production"):
                        try:
                            text = p.read_text(encoding="utf-8", errors="ignore")
                            secrets = detect_secrets(text)
                            if secrets:
                                secret_detected = 1
                            summary = text[:500].replace("\n", " ")
                        except Exception as e:
                            unreadable = str(e)

                    category = guess_category(p, summary)
                    ai_tool = guess_ai_tool(p)
                    reusable = 1 if category in ("Feature", "Workflow", "Prompt", "Agent", "Infrastructure") else 0
                    revenue_linked = 1 if any(x in spath.lower() for x in ["product", "service", "client", "stripe", "revenue", "sale", "youtube", "monet"]) else 0

                    if spath in existing:
                        old = existing[spath]
                        if old["sha256"] != sha or old["modified_at"] != mtime:
                            files_changed += 1
                            updated_rows.append({
                                "path": spath,
                                "filename": p.name,
                                "extension": ext,
                                "size_bytes": size,
                                "sha256": sha,
                                "modified_at": mtime,
                                "last_scanned_at": now,
                                "category": category,
                                "status": old["status"] if old["status"] != "Archived" else "Needs Review",
                                "ai_tool_guess": ai_tool,
                                "summary": summary,
                                "reusable": reusable,
                                "revenue_linked": revenue_linked,
                                "secret_detected": secret_detected,
                                "unreadable_reason": unreadable,
                            })
                    else:
                        new_rows.append({
                            "path": spath,
                            "filename": p.name,
                            "extension": ext,
                            "size_bytes": size,
                            "sha256": sha,
                            "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
                            "modified_at": mtime,
                            "last_scanned_at": now,
                            "category": category,
                            "status": "Active",
                            "ai_tool_guess": ai_tool,
                            "summary": summary,
                            "reusable": reusable,
                            "revenue_linked": revenue_linked,
                            "secret_detected": secret_detected,
                            "unreadable_reason": unreadable,
                        })
                except Exception as e:
                    errors += 1
            if time.time() - start_time > MAX_TIME or files_seen >= MAX_FILES:
                break
        except Exception as e:
            errors += 1

    # Mark missing files as archived
    missing = set(existing.keys()) - seen_paths

    with get_conn() as conn:
        for row in new_rows:
            conn.execute(
                """INSERT INTO files
                (path, filename, extension, size_bytes, sha256, created_at, modified_at, last_scanned_at, category, status, ai_tool_guess, summary, reusable, revenue_linked, secret_detected, unreadable_reason)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                tuple(row.get(k) for k in [
                    "path", "filename", "extension", "size_bytes", "sha256", "created_at", "modified_at",
                    "last_scanned_at", "category", "status", "ai_tool_guess", "summary",
                    "reusable", "revenue_linked", "secret_detected", "unreadable_reason"
                ])
            )
        for row in updated_rows:
            conn.execute(
                """UPDATE files SET
                filename=?, extension=?, size_bytes=?, sha256=?, modified_at=?, last_scanned_at=?,
                category=?, status=?, ai_tool_guess=?, summary=?, reusable=?, revenue_linked=?,
                secret_detected=?, unreadable_reason=?
                WHERE path=?""",
                (row["filename"], row["extension"], row["size_bytes"], row["sha256"], row["modified_at"],
                 row["last_scanned_at"], row["category"], row["status"], row["ai_tool_guess"], row["summary"],
                 row["reusable"], row["revenue_linked"], row["secret_detected"], row["unreadable_reason"],
                 row["path"]),
            )
        for mpath in missing:
            conn.execute("UPDATE files SET status='Archived' WHERE path=?", (mpath,))
        conn.execute(
            "UPDATE scans SET finished_at=?, files_seen=?, files_changed=?, errors=?, status=?, notes=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(), files_seen, files_changed, errors, "done", f"New {len(new_rows)}, Updated {len(updated_rows)}, Missing {len(missing)}", scan_id),
        )
        conn.commit()

    return {
        "scan_id": scan_id,
        "files_seen": files_seen,
        "files_changed": files_changed,
        "errors": errors,
        "new": len(new_rows),
        "updated": len(updated_rows),
        "missing_archived": len(missing),
    }
