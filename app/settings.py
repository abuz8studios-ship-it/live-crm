"""ABUZ8 LIVE CRM Settings"""
import os
from pathlib import Path

CRM_ROOT = Path("./LIVE_CRM")
APP_DIR = CRM_ROOT / "app"
WEB_DIR = CRM_ROOT / "web"
DATA_DIR = CRM_ROOT / "data"
SCRIPTS_DIR = CRM_ROOT / "scripts"
REPORTS_DIR = CRM_ROOT / "reports"

DB_PATH = DATA_DIR / "abu_crm.sqlite"
AGENT_REGISTRY_PATH = DATA_DIR / "agent_registry.json"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
EXPORTS_DIR = DATA_DIR / "exports"

SCAN_ROOTS = ["E:\\", "C:\\Users\\USER"]
HIGH_PRIORITY_PATHS = [
    "E:\\ABU",
    "C:\\Users\\USER",
    "C:\\Users\\USER\\Desktop",
    "C:\\Users\\USER\\Documents",
    "C:\\Users\\USER\\Downloads",
    "C:\\Users\\USER\\ComfyUI",
]

SAFE_EXTENSIONS = {
    ".md", ".txt", ".json", ".yaml", ".yml", ".py", ".js", ".ts",
    ".html", ".css", ".ps1", ".bat", ".sh", ".csv", ".docx", ".pdf",
    ".xml", ".sql", ".env.example"
}

MODEL_EXTENSIONS = {
    ".safetensors", ".gguf", ".bin", ".pt", ".pth", ".ckpt",
    ".onnx", ".pb", ".h5"
}

EXCLUDED_DIRS = {
    "node_modules", ".git", "venv", ".venv", "__pycache__",
    "cache", "dist", "build", ".cache", "temp", "tmp",
    "package cache", "windows", "program files", "program files (x86)",
    "appdata\\local\\temp"
}

SECRET_PATTERNS = [
    (r"api[_-]?key\s*[:=]\s*['\"]?([\w\-]{20,})['\"]?", "api_key"),
    (r"token\s*[:=]\s*['\"]?([\w\-]{20,})['\"]?", "token"),
    (r"password\s*[:=]\s*['\"]?([^'\"\s]{8,})['\"]?", "password"),
    (r"secret\s*[:=]\s*['\"]?([\w\-]{20,})['\"]?", "secret"),
    (r"sk-[a-zA-Z0-9]{20,}", "api_key"),
    (r"AKIA[0-9A-Z]{16}", "api_key"),
]

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
