"""Installed programs scanner for ABUZ8 CRM"""
import os
import re
import subprocess
import winreg
from datetime import datetime, timezone
from pathlib import Path
from .db import get_conn


AI_ML_PROGRAMS = {
    "ollama", "comfyui", "lm studio", "open webui", "automatic1111", "forge",
    "invokeai", "pinokio", "jan.ai", "gpt4all", "rvc", "whisper", "kokoro",
}

DEV_PROGRAMS = {
    "python", "conda", "node.js", "npm", "git", "docker", "vs code", "cursor",
    "redis", "postgresql", "sqlite",
}

AUTO_PROGRAMS = {
    "playwright", "selenium", "puppeteer",
}

BIZ_PROGRAMS = {
    "office", "pdf", "notion", "obsidian", "telegram", "discord",
}

MEDIA_PROGRAMS = {
    "premiere", "after effects", "davinci", "blender", "photoshop", "gimp",
    "audacity", "obs", "bandicam", "camtasia",
}


def categorize(name: str) -> str:
    nl = name.lower()
    if any(x in nl for x in AI_ML_PROGRAMS):
        return "AI/ML"
    if any(x in nl for x in DEV_PROGRAMS):
        return "Development"
    if any(x in nl for x in AUTO_PROGRAMS):
        return "Automation"
    if any(x in nl for x in BIZ_PROGRAMS):
        return "Business/Productivity"
    if any(x in nl for x in MEDIA_PROGRAMS):
        return "Media"
    return "Other"


def role_in_stack(name: str, category: str) -> str:
    nl = name.lower()
    if "ollama" in nl:
        return "Local LLM inference"
    if "comfy" in nl:
        return "Image/Video generation"
    if "cursor" in nl or "vs code" in nl:
        return "IDE / Code editing"
    if "python" in nl:
        return "Runtime"
    if "node" in nl or "npm" in nl:
        return "JS runtime"
    if "docker" in nl:
        return "Containerization"
    if "git" in nl:
        return "Version control"
    if "postgres" in nl or "sqlite" in nl or "redis" in nl:
        return "Database"
    if category == "AI/ML":
        return "AI/ML tool"
    return "General"


def get_uninstall_programs():
    programs = []
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hkey, path in keys:
        try:
            with winreg.OpenKey(hkey, path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subname = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subname) as subkey:
                            name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            version = winreg.QueryValueEx(subkey, "DisplayVersion")[0] if "DisplayVersion" in [winreg.EnumValue(subkey, j)[0] for j in range(winreg.QueryInfoKey(subkey)[1])] else ""
                            install_location = ""
                            try:
                                install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                            except Exception:
                                pass
                            size = 0
                            try:
                                size = int(winreg.QueryValueEx(subkey, "EstimatedSize")[0]) * 1024
                            except Exception:
                                pass
                            programs.append({
                                "name": name,
                                "version": version,
                                "path": install_location,
                                "size_bytes": size,
                            })
                    except Exception:
                        pass
        except Exception:
            pass
    return programs


def get_path_programs():
    found = []
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    known_exes = {
        "python.exe": "Python",
        "node.exe": "Node.js",
        "git.exe": "Git",
        "docker.exe": "Docker",
        "code.exe": "VS Code",
        "cursor.exe": "Cursor",
        "ollama.exe": "Ollama",
        "obs64.exe": "OBS",
    }
    for d in path_dirs:
        pd = Path(d)
        if not pd.exists():
            continue
        for exe, label in known_exes.items():
            fp = pd / exe
            if fp.exists():
                found.append({
                    "name": label,
                    "version": "",
                    "path": str(fp),
                    "size_bytes": fp.stat().st_size if fp.exists() else 0,
                })
    return found


def scan_programs():
    now = datetime.now(timezone.utc).isoformat()
    scan_id = None
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO scans (scan_type, started_at, status) VALUES (?,?,?)",
            ("programs", now, "running"),
        )
        scan_id = cur.lastrowid
        conn.commit()

    all_progs = {}
    for p in get_uninstall_programs():
        all_progs[p["name"].lower()] = p
    for p in get_path_programs():
        all_progs[p["name"].lower()] = p

    with get_conn() as conn:
        for p in all_progs.values():
            cat = categorize(p["name"])
            role = role_in_stack(p["name"], cat)
            existing = conn.execute("SELECT id FROM programs WHERE name=?", (p["name"],)).fetchone()
            if existing:
                conn.execute(
                    """UPDATE programs SET version=?, path=?, category=?, status=?, role_in_stack=?, notes=? WHERE id=?""",
                    (p["version"], p["path"], cat, "Active", role, f"Size: {p.get('size_bytes', 0)}", existing["id"]),
                )
            else:
                conn.execute(
                    """INSERT INTO programs (name, version, path, category, status, last_used, role_in_stack, notes)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (p["name"], p["version"], p["path"], cat, "Active", "", role, f"Size: {p.get('size_bytes', 0)}"),
                )
        conn.execute(
            "UPDATE scans SET finished_at=?, files_seen=?, files_changed=?, errors=?, status=?, notes=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(), len(all_progs), 0, 0, "done", f"Programs found: {len(all_progs)}", scan_id),
        )
        conn.commit()

    return {"scan_id": scan_id, "programs_found": len(all_progs)}
