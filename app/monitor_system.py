"""System monitor for ABUZ8 CRM"""
import json
import subprocess
import psutil
from datetime import datetime, timezone
from .db import get_conn


def get_gpu_info():
    gpus = []
    gpu_processes = []
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            for i, line in enumerate(result.stdout.strip().splitlines()):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    gpus.append({
                        "index": i,
                        "name": parts[0],
                        "vram_used_mb": float(parts[1]),
                        "vram_total_mb": float(parts[2]),
                        "util_pct": float(parts[3]),
                    })
    except Exception as e:
        gpus.append({"index": 0, "name": f"nvidia-smi error: {e}", "vram_used_mb": 0, "vram_total_mb": 0, "util_pct": 0})

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,name,gpu_uuid,used_memory",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    gpu_processes.append({
                        "pid": parts[0],
                        "name": parts[1],
                        "gpu_uuid": parts[2],
                        "used_memory_mb": float(parts[3]),
                    })
    except Exception:
        pass

    return gpus, gpu_processes


def get_disk_info():
    disks = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": usage.percent,
            })
        except Exception:
            pass
    return disks


def get_running_services():
    services = []
    targets = ["ollama", "comfy", "open-webui", "fastapi", "uvicorn", "python", "node", "docker"]
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = proc.info["name"] or ""
            cmd = " ".join(proc.info["cmdline"] or [])
            lower = f"{name} {cmd}".lower()
            for t in targets:
                if t in lower:
                    services.append({
                        "pid": proc.info["pid"],
                        "name": name,
                        "cmdline": cmd[:200],
                        "matched": t,
                    })
                    break
        except Exception:
            pass
    return services


def get_open_ports():
    ports = []
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port:
                ports.append({
                    "port": conn.laddr.port,
                    "pid": conn.pid,
                    "status": conn.status,
                })
    except Exception:
        pass
    return ports


def capture_system_metrics():
    now = datetime.now(timezone.utc).isoformat()
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disks = get_disk_info()
    gpus, gpu_procs = get_gpu_info()
    services = get_running_services()
    ports = get_open_ports()

    gpu0 = gpus[0] if len(gpus) > 0 else {"name": None, "vram_used_mb": 0, "vram_total_mb": 0, "util_pct": 0}
    gpu1 = gpus[1] if len(gpus) > 1 else {"name": None, "vram_used_mb": 0, "vram_total_mb": 0, "util_pct": 0}

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO system_metrics
            (timestamp, cpu_pct, ram_used_gb, ram_total_gb,
             gpu0_name, gpu0_vram_used_gb, gpu0_vram_total_gb, gpu0_util_pct,
             gpu1_name, gpu1_vram_used_gb, gpu1_vram_total_gb, gpu1_util_pct,
             disk_json, gpu_processes_json, running_services_json, open_ports_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                now,
                round(cpu, 1),
                round(mem.used / (1024**3), 2),
                round(mem.total / (1024**3), 2),
                gpu0.get("name"),
                round(gpu0.get("vram_used_mb", 0) / 1024, 2),
                round(gpu0.get("vram_total_mb", 0) / 1024, 2),
                round(gpu0.get("util_pct", 0), 1),
                gpu1.get("name"),
                round(gpu1.get("vram_used_mb", 0) / 1024, 2),
                round(gpu1.get("vram_total_mb", 0) / 1024, 2),
                round(gpu1.get("util_pct", 0), 1),
                json.dumps(disks),
                json.dumps(gpu_procs),
                json.dumps(services),
                json.dumps(ports),
            ),
        )
        conn.commit()

    return {
        "timestamp": now,
        "cpu_pct": cpu,
        "ram_used_gb": round(mem.used / (1024**3), 2),
        "ram_total_gb": round(mem.total / (1024**3), 2),
        "gpu0": gpu0,
        "gpu1": gpu1,
        "services_count": len(services),
        "ports_count": len(ports),
    }
