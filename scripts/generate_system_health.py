import json
from app.db import get_conn
from app.settings import REPORTS_DIR
from pathlib import Path

with get_conn() as conn:
    row = conn.execute("SELECT * FROM system_metrics ORDER BY id DESC LIMIT 1").fetchone()

if not row:
    text = "# System Health\n\nNo metrics yet.\n"
else:
    r = dict(row)
    text = "# System Health\n\n"
    text += f"- CPU: {r['cpu_pct']}%\n"
    text += f"- RAM: {r['ram_used_gb']} / {r['ram_total_gb']} GB\n"
    text += f"- GPU0: {r['gpu0_name'] or 'N/A'} | Util: {r['gpu0_util_pct']}% | VRAM: {r['gpu0_vram_used_gb']}/{r['gpu0_vram_total_gb']} GB\n"
    text += f"- GPU1: {r['gpu1_name'] or 'N/A'} | Util: {r['gpu1_util_pct']}% | VRAM: {r['gpu1_vram_used_gb']}/{r['gpu1_vram_total_gb']} GB\n"
    disks = json.loads(r['disk_json'] or '[]')
    text += "\n## Disks\n"
    for d in disks:
        text += f"- {d['device']} {d['mountpoint']}: {d['used_gb']}/{d['total_gb']} GB ({d['percent']}%)\n"
    svcs = json.loads(r['running_services_json'] or '[]')
    text += f"\n## Running Services ({len(svcs)})\n"
    for s in svcs[:15]:
        text += f"- {s['matched']}: PID {s['pid']} {s['name']}\n"
    ports = json.loads(r['open_ports_json'] or '[]')
    text += f"\n## Open Ports ({len(ports)})\n"
    for p in ports[:20]:
        text += f"- Port {p['port']} PID {p['pid']} {p['status']}\n"

Path(REPORTS_DIR / 'system_health.md').write_text(text, encoding='utf-8')
print('System health report written')
