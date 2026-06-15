"""ABUZ8 LIVE CRM Database Layer"""
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from .settings import DB_PATH, DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)

INIT_SQL = """
-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    category TEXT,
    status TEXT,
    completion_pct INTEGER DEFAULT 0,
    evidence_score INTEGER DEFAULT 0,
    revenue_potential REAL DEFAULT 0,
    revenue_realized REAL DEFAULT 0,
    market_value_verified REAL DEFAULT 0,
    replacement_cost_value REAL DEFAULT 0,
    strategic_upside_value REAL DEFAULT 0,
    valuation_confidence INTEGER DEFAULT 0,
    valuation_method TEXT,
    priority_score INTEGER DEFAULT 0,
    urf_urgency INTEGER DEFAULT 5,
    urf_reality INTEGER DEFAULT 5,
    urf_feasibility INTEGER DEFAULT 5,
    urf_score REAL DEFAULT 0,
    today_score REAL DEFAULT 0,
    next_action TEXT,
    next_action_eta_hours REAL DEFAULT 999,
    blocker TEXT,
    assigned_agent TEXT,
    created_at TEXT,
    last_active_at TEXT,
    updated_at TEXT,
    notes TEXT
);

-- Files
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE,
    filename TEXT,
    extension TEXT,
    size_bytes INTEGER,
    sha256 TEXT,
    created_at TEXT,
    modified_at TEXT,
    last_scanned_at TEXT,
    project_id INTEGER,
    category TEXT,
    status TEXT,
    ai_tool_guess TEXT,
    summary TEXT,
    reusable INTEGER DEFAULT 0,
    revenue_linked INTEGER DEFAULT 0,
    secret_detected INTEGER DEFAULT 0,
    unreadable_reason TEXT
);

-- Models
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    model_type TEXT,
    architecture TEXT,
    path TEXT UNIQUE,
    size_bytes INTEGER,
    modified_at TEXT,
    source TEXT,
    status TEXT,
    vram_required_gb REAL,
    commercial_license_status TEXT DEFAULT 'Unknown / Needs Review',
    duplicate_group TEXT,
    notes TEXT
);

-- Programs
CREATE TABLE IF NOT EXISTS programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    version TEXT,
    path TEXT,
    category TEXT,
    status TEXT,
    last_used TEXT,
    role_in_stack TEXT,
    notes TEXT
);

-- Agents
CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    framework TEXT,
    status TEXT,
    process_id INTEGER,
    port INTEGER,
    endpoint TEXT,
    model_used TEXT,
    gpu_id TEXT,
    last_heartbeat TEXT,
    current_task TEXT,
    notes TEXT
);

-- System Metrics
CREATE TABLE IF NOT EXISTS system_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    cpu_pct REAL,
    ram_used_gb REAL,
    ram_total_gb REAL,
    gpu0_name TEXT,
    gpu0_vram_used_gb REAL,
    gpu0_vram_total_gb REAL,
    gpu0_util_pct REAL,
    gpu1_name TEXT,
    gpu1_vram_used_gb REAL,
    gpu1_vram_total_gb REAL,
    gpu1_util_pct REAL,
    disk_json TEXT,
    gpu_processes_json TEXT,
    running_services_json TEXT,
    open_ports_json TEXT
);

-- Scans
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_type TEXT,
    started_at TEXT,
    finished_at TEXT,
    files_seen INTEGER DEFAULT 0,
    files_changed INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    status TEXT,
    notes TEXT
);

-- Actions
CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    action TEXT,
    reason TEXT,
    eta_hours REAL,
    money_unlocked REAL,
    status TEXT,
    due_date TEXT,
    created_at TEXT,
    completed_at TEXT,
    assigned_agent TEXT
);

-- Comfy Jobs
CREATE TABLE IF NOT EXISTS comfy_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    workflow_path TEXT,
    prompt_path TEXT,
    model_used TEXT,
    status TEXT,
    output_path TEXT,
    target_video_count INTEGER DEFAULT 0,
    completed_video_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    next_render_action TEXT,
    last_run_at TEXT,
    notes TEXT
);

-- Project Checklists
CREATE TABLE IF NOT EXISTS project_checklists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    step_number INTEGER,
    description TEXT,
    eta_hours REAL,
    is_done INTEGER DEFAULT 0,
    money_path TEXT,
    required_files TEXT,
    required_agent TEXT,
    created_at TEXT
);

-- Snapshots
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    snapshot_type TEXT,
    path TEXT,
    summary TEXT
);
"""

PRELOAD_PROJECTS = [
    ("Qadir Core / Hermes / MCP brain", "Agent", "Needs Review", 30, "Qadir", "Core LLM orchestration and MCP integration. Needs hardening."),
    ("Zait / OpenClaw operator", "Agent", "Needs Review", 40, "Zait", "Browser automation and task execution layer."),
    ("Mission Control Dashboard", "Infrastructure", "Active", 80, "Kimi", "This CRM dashboard itself."),
    ("ComfyUI Media Factory", "Infrastructure", "Active", 60, "ComfyUI", "Image and video generation pipeline."),
    ("YouTube 50 one-minute video push", "Content", "Active", 10, "ComfyUI", "Short-form video production target."),
    ("Avatar Stack", "Content", "Needs Review", 20, "ComfyUI", "Avatar generation and consistency pipeline."),
    ("Agent Zero integration", "Agent", "Needs Review", 15, "Agent Zero", "Autonomous agent framework integration."),
    ("LotVue360", "Product", "Needs Review", 25, "Qadir", "360 property viewing product. Needs customer validation."),
    ("PM Workflow Rescue", "Product", "Needs Review", 30, "Zait", "Project management automation service."),
    ("LinkedIn Service Audit", "Research", "Needs Review", 10, "Zait", "LinkedIn outreach and audit offering."),
    ("PDF Knowledge Extractor", "Product", "Needs Review", 35, "Qadir", "Document parsing and knowledge extraction."),
    ("URF Scoring Engine", "Infrastructure", "Needs Review", 50, "Kimi", "Urgency-Reality-Feasibility scoring system."),
    ("ABUZ8 Website / abuz8ai.com", "Product", "Needs Review", 20, "Zait", "Public-facing brand site."),
    ("Open WebUI / Ollama local brain", "Infrastructure", "Active", 70, "Ollama", "Local LLM inference stack."),
    ("RVC / voice stack", "Content", "Needs Review", 15, "RVC", "Voice cloning and TTS pipeline."),
    ("Kinect voice capture stack", "Infrastructure", "Needs Review", 5, "RVC", "Legacy voice capture hardware integration."),
]

PRELOAD_GRAVEYARD = [
    ("Archived Project B", "Graveyard", "Killed", 0, "None", "No evidence of utility or market demand. Do not revive without revenue proof."),
    ("Archived Project A", "Graveyard", "Killed", 0, "None", "No regulatory path or buyer identified."),
    ("Archived Project C", "Graveyard", "Killed", 0, "None", "Superseded by direct service model."),
    ("Archived Project D", "Graveyard", "Killed", 0, "None", "Consolidate to single current version only."),
    ("Archived Project E", "Graveyard", "Killed", 0, "None", "Superseded by LotVue360 if validated."),
    ("Archived Project F", "Graveyard", "Killed", 0, "None", "Superseded by current Avatar Stack."),
]


def init_db():
    with get_conn() as conn:
        conn.executescript(INIT_SQL)
        # Preload projects if empty
        cur = conn.execute("SELECT COUNT(*) FROM projects")
        if cur.fetchone()[0] == 0:
            now = datetime.now(timezone.utc).isoformat()
            for name, cat, status, comp, agent, notes in PRELOAD_PROJECTS + PRELOAD_GRAVEYARD:
                conn.execute(
                    """INSERT INTO projects
                    (name, category, status, completion_pct, assigned_agent, created_at, last_active_at, updated_at, notes)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (name, cat, status, comp, agent, now, now, now, notes)
                )
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}
