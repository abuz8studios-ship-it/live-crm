"""AI Model + ComfyUI scanner for ABUZ8 CRM"""
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from .db import get_conn
from .settings import MODEL_EXTENSIONS, EXCLUDED_DIRS


def should_skip_dir(p: Path) -> bool:
    parts = [part.lower() for part in p.parts]
    for ex in EXCLUDED_DIRS:
        if ex.lower() in parts:
            return True
    return False


def infer_model_type(path: Path) -> str:
    p = str(path).lower()
    if "checkpoint" in p or "sdxl" in p or "sd1.5" in p:
        return "Checkpoint"
    if "lora" in p:
        return "LoRA"
    if "controlnet" in p:
        return "ControlNet"
    if "vae" in p:
        return "VAE"
    if "clip" in p:
        return "CLIP"
    if "unet" in p or "diffusion_model" in p:
        return "UNet/Diffusion"
    if "upscale" in p:
        return "Upscaler"
    if "ipadapter" in p:
        return "IPAdapter"
    if "inpaint" in p:
        return "Inpainting"
    if "video" in p:
        return "Video"
    if ".gguf" in p:
        return "GGUF (LLM)"
    if "whisper" in p:
        return "Whisper"
    if "rvc" in p:
        return "RVC"
    if "kokoro" in p or "tts" in p:
        return "TTS"
    if "embed" in p:
        return "Embedding"
    return "Unknown"


def infer_architecture(path: Path) -> str:
    p = path.name.lower()
    if "sdxl" in p:
        return "SDXL"
    if "sd1.5" in p or "sd-1.5" in p:
        return "SD 1.5"
    if "flux" in p:
        return "Flux"
    if "pony" in p:
        return "Pony"
    if "llama" in p:
        return "Llama"
    if "mistral" in p:
        return "Mistral"
    if "qwen" in p:
        return "Qwen"
    if "deepseek" in p:
        return "DeepSeek"
    return "Unknown"


def scan_ollama():
    models = []
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 3:
                    models.append({
                        "name": parts[0],
                        "model_type": "Ollama LLM",
                        "architecture": "Unknown",
                        "path": f"ollama://{parts[0]}",
                        "size_bytes": 0,
                        "modified_at": datetime.now(timezone.utc).isoformat(),
                        "source": "Ollama",
                        "status": "Active",
                        "vram_required_gb": None,
                        "commercial_license_status": "Unknown / Needs Review",
                        "duplicate_group": None,
                        "notes": f"ID {parts[1]} Size {parts[2]}",
                    })
    except Exception:
        pass
    return models


def scan_comfy_models(root: Path):
    found = []
    comfy_dirs = [
        "models/checkpoints", "models/loras", "models/controlnet",
        "models/vae", "models/clip", "models/unet", "models/diffusion_models",
        "models/text_encoders", "models/upscale_models", "models/ipadapter",
        "models/inpaint", "models/video", "custom_nodes",
    ]
    for sub in comfy_dirs:
        d = root / sub
        if not d.exists():
            continue
        try:
            for p in d.rglob("*"):
                if p.is_file() and p.suffix.lower() in MODEL_EXTENSIONS:
                    stat = p.stat()
                    found.append({
                        "name": p.name,
                        "model_type": infer_model_type(p),
                        "architecture": infer_architecture(p),
                        "path": str(p.resolve()),
                        "size_bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                        "source": "ComfyUI",
                        "status": "Active",
                        "vram_required_gb": None,
                        "commercial_license_status": "Unknown / Needs Review",
                        "duplicate_group": None,
                        "notes": f"Folder: {sub}",
                    })
        except Exception:
            pass
    return found


def fast_walk_models(root: Path, max_files: int = 3000, max_time: float = 20.0):
    found = []
    start = time.time()
    for dirpath, dirnames, filenames in os.walk(root):
        if time.time() - start > max_time or len(found) >= max_files:
            break
        # Prune excluded dirs
        dirnames[:] = [d for d in dirnames if d.lower() not in EXCLUDED_DIRS and not d.startswith('.')]
        for fn in filenames:
            if time.time() - start > max_time or len(found) >= max_files:
                break
            if any(fn.lower().endswith(ext) for ext in MODEL_EXTENSIONS):
                fp = Path(dirpath) / fn
                try:
                    stat = fp.stat()
                    found.append({
                        "name": fp.name,
                        "model_type": infer_model_type(fp),
                        "architecture": infer_architecture(fp),
                        "path": str(fp.resolve()),
                        "size_bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                        "source": "Filesystem",
                        "status": "Active",
                        "vram_required_gb": None,
                        "commercial_license_status": "Unknown / Needs Review",
                        "duplicate_group": None,
                        "notes": "",
                    })
                except Exception:
                    pass
    return found


def deduplicate_candidates(models: list) -> list:
    by_name = {}
    for m in models:
        key = m["name"].lower()
        by_name.setdefault(key, []).append(m)
    for key, group in by_name.items():
        if len(group) > 1:
            dup_id = f"dup_{key}"
            for m in group:
                m["duplicate_group"] = dup_id
    return models


def scan_models():
    now = datetime.now(timezone.utc).isoformat()
    scan_id = None
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO scans (scan_type, started_at, status) VALUES (?,?,?)",
            ("models", now, "running"),
        )
        scan_id = cur.lastrowid
        conn.commit()

    all_models = []
    all_models.extend(scan_ollama())

    # Known ComfyUI roots only
    comfy_roots = [Path("~/ComfyUI")]
    for cr in comfy_roots:
        if cr.exists():
            all_models.extend(scan_comfy_models(cr))

    # Fast walk limited scope
    for root in [Path("."), Path("~")]:
        if root.exists():
            all_models.extend(fast_walk_models(root, max_files=2000, max_time=15))

    all_models = deduplicate_candidates(all_models)

    with get_conn() as conn:
        for m in all_models:
            existing = conn.execute("SELECT id FROM models WHERE path=?", (m["path"],)).fetchone()
            vals = tuple(m.get(k) for k in [
                "name", "model_type", "architecture", "path", "size_bytes", "modified_at",
                "source", "status", "vram_required_gb", "commercial_license_status",
                "duplicate_group", "notes"
            ])
            if existing:
                conn.execute(
                    """UPDATE models SET name=?, model_type=?, architecture=?, size_bytes=?, modified_at=?, source=?, status=?, vram_required_gb=?, commercial_license_status=?, duplicate_group=?, notes=? WHERE id=?""",
                    vals[:-1] + (existing["id"],),
                )
            else:
                conn.execute(
                    """INSERT INTO models (name, model_type, architecture, path, size_bytes, modified_at, source, status, vram_required_gb, commercial_license_status, duplicate_group, notes)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    vals,
                )
        conn.execute(
            "UPDATE scans SET finished_at=?, files_seen=?, files_changed=?, errors=?, status=?, notes=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(), len(all_models), 0, 0, "done", f"Models found: {len(all_models)}", scan_id),
        )
        conn.commit()

    return {"scan_id": scan_id, "models_found": len(all_models)}
