"""Agent monitor for ABUZ8 CRM"""
import json
import psutil
import socket
from datetime import datetime, timezone
from pathlib import Path
from .db import get_conn
from .settings import AGENT_REGISTRY_PATH


AGENT_SIGNATURES = [
    {"name": "Ollama", "framework": "Ollama", "process_names": ["ollama.exe", "ollama"], "ports": [11434], "endpoint": "http://localhost:11434"},
    {"name": "ComfyUI", "framework": "ComfyUI", "process_names": ["python.exe", "python"], "ports": [8188], "endpoint": "http://localhost:8188", "cmd_hint": "comfy"},
    {"name": "Open WebUI", "framework": "Open WebUI", "process_names": ["python.exe", "python"], "ports": [8080], "endpoint": "http://localhost:8080", "cmd_hint": "open-webui"},
    {"name": "LM Studio", "framework": "LM Studio", "process_names": ["lm-studio.exe", "lm-studio"], "ports": [1234], "endpoint": "http://localhost:1234"},
    {"name": "Cursor", "framework": "Cursor", "process_names": ["cursor.exe", "cursor"], "ports": [], "endpoint": ""},
    {"name": "Claude Code", "framework": "Claude Code", "process_names": ["claude.exe", "claude"], "ports": [], "endpoint": ""},
    {"name": "Kimi Code", "framework": "Kimi Code", "process_names": ["kimi.exe", "kimi"], "ports": [], "endpoint": ""},
    {"name": "OpenCode", "framework": "OpenCode", "process_names": ["opencod.exe", "opencod"], "ports": [], "endpoint": ""},
    {"name": "Zait / OpenClaw", "framework": "OpenClaw", "process_names": ["python.exe", "python"], "ports": [], "endpoint": "", "cmd_hint": "openclaw"},
    {"name": "Qadir / Hermes", "framework": "Hermes", "process_names": ["python.exe", "python"], "ports": [], "endpoint": "", "cmd_hint": "hermes"},
    {"name": "Agent Zero", "framework": "Agent Zero", "process_names": ["python.exe", "python"], "ports": [], "endpoint": "", "cmd_hint": "agent-zero"},
    {"name": "Playwright", "framework": "Playwright", "process_names": ["node.exe", "node"], "ports": [], "endpoint": "", "cmd_hint": "playwright"},
]


def check_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def discover_agents():
    now = datetime.now(timezone.utc).isoformat()
    results = []
    seen_pids = set()

    for sig in AGENT_SIGNATURES:
        status = "DOWN"
        pid = None
        port = None
        endpoint = sig.get("endpoint", "")
        model_used = ""
        gpu_id = ""
        current_task = ""

        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["pid"] in seen_pids:
                    continue
                pname = (proc.info["name"] or "").lower()
                cmd = " ".join(proc.info["cmdline"] or []).lower()
                match = False
                for pn in sig["process_names"]:
                    if pn.lower() == pname:
                        match = True
                        break
                if not match and sig.get("cmd_hint"):
                    if sig["cmd_hint"].lower() in cmd:
                        match = True
                if match:
                    pid = proc.info["pid"]
                    seen_pids.add(pid)
                    break
            except Exception:
                pass

        if pid:
            status = "IDLE"
            for p in sig.get("ports", []):
                if check_port_open("127.0.0.1", p):
                    port = p
                    status = "LIVE"
                    break

        # Load task from registry file if exists
        registry_file = Path(f"~/.{sig['name'].split('/')[0].strip().lower()}_task.json")
        if registry_file.exists():
            try:
                data = json.loads(registry_file.read_text(encoding="utf-8"))
                current_task = data.get("current_task", "")
            except Exception:
                pass

        results.append({
            "name": sig["name"],
            "framework": sig["framework"],
            "status": status,
            "process_id": pid,
            "port": port,
            "endpoint": endpoint,
            "model_used": model_used,
            "gpu_id": gpu_id,
            "last_heartbeat": now if pid else None,
            "current_task": current_task,
            "notes": "",
        })

    with get_conn() as conn:
        for a in results:
            existing = conn.execute("SELECT id FROM agents WHERE name=?", (a["name"],)).fetchone()
            vals = tuple(a.get(k) for k in [
                "name", "framework", "status", "process_id", "port", "endpoint",
                "model_used", "gpu_id", "last_heartbeat", "current_task", "notes"
            ])
            if existing:
                conn.execute(
                    """UPDATE agents SET framework=?, status=?, process_id=?, port=?, endpoint=?, model_used=?, gpu_id=?, last_heartbeat=?, current_task=?, notes=? WHERE id=?""",
                    vals[1:] + (existing["id"],),
                )
            else:
                conn.execute(
                    """INSERT INTO agents (name, framework, status, process_id, port, endpoint, model_used, gpu_id, last_heartbeat, current_task, notes)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    vals,
                )
        conn.commit()

    if AGENT_REGISTRY_PATH:
        AGENT_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        AGENT_REGISTRY_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")

    return results
