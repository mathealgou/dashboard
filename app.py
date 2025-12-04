import re
import time

import psutil
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

SERVICES = [
    {"key": "nas", "name": "NAS", "url": "https://nas.mathealgou.org/"},
    {"key": "notes", "name": "Notes", "url": "http://notes.mathealgou.org/"},
    {"key": "movies", "name": "Movies", "url": "https://movies.mathealgou.org/"},
]


@app.route("/")
def dashboard():
    """Serve the blank dashboard page."""
    return render_template("dashboard.html", services=SERVICES)


@app.route("/api/status")
def service_status():
    """Return health information for each configured service."""
    results = []
    for service in SERVICES:
        entry = {
            "key": service["key"],
            "name": service["name"],
            "url": service["url"],
            "status": "unknown",
            "message": "Checking",
        }
        try:
            response = requests.get(service["url"], timeout=5)
            if response.ok:
                entry["status"] = "up"
                entry["message"] = "Online"
            else:
                entry["status"] = "down"
                entry["message"] = f"Error {response.status_code}"
        except requests.RequestException:
            entry["status"] = "down"
            entry["message"] = "Unreachable"
        results.append(entry)
    return jsonify({"services": results})


def _cpu_temperature_c():
    """Best-effort CPU temperature lookup."""
    try:
        temps = psutil.sensors_temperatures()
    except (AttributeError, NotImplementedError):
        return None
    if not temps:
        return None
    preferred_keys = ("coretemp", "cpu-thermal", "cpu_thermal", "k10temp")
    for key in preferred_keys:
        if key in temps and temps[key]:
            return temps[key][0].current
    for readings in temps.values():
        if readings:
            return readings[0].current
    return None


def _canonical_device(device):
    """Map a partition device path to its underlying physical device."""
    if not device:
        return None

    patterns = (
        re.compile(r"(?P<base>/dev/nvme\d+n\d+)p\d+$"),
        re.compile(r"(?P<base>/dev/mmcblk\d+)p\d+$"),
        re.compile(r"(?P<base>/dev/(?:sd|hd|vd|xvd)[a-z]+)\d+$"),
    )
    for pattern in patterns:
        match = pattern.match(device)
        if match:
            return match.group("base")
    general = re.match(r"(?P<base>/dev/[a-zA-Z]+)\d+$", device)
    if general:
        return general.group("base")
    return device


def _disk_usage_all():
    """Collect usage information aggregated per physical disk."""
    aggregates = {}
    try:
        partitions = psutil.disk_partitions(all=False)
    except Exception:  # pragma: no cover - defensive
        partitions = []

    seen_mounts = set()
    for part in partitions:
        mount = part.mountpoint
        device = part.device
        if not mount or not device or mount in seen_mounts:
            continue
        if not device.startswith("/dev/"):
            continue
        seen_mounts.add(mount)
        try:
            usage = psutil.disk_usage(mount)
        except (PermissionError, FileNotFoundError, OSError):
            continue
        key = _canonical_device(device) or device
        bucket = aggregates.setdefault(
            key,
            {
                "device": key,
                "mounts": set(),
                "fstypes": set(),
                "total": 0,
                "used": 0,
            },
        )
        bucket["mounts"].add(mount)
        if part.fstype:
            bucket["fstypes"].add(part.fstype)
        bucket["total"] += usage.total
        bucket["used"] += usage.used

    disks = []
    for bucket in aggregates.values():
        total = bucket["total"]
        used = min(bucket["used"], total)
        percent = (used / total * 100) if total else 0
        disks.append(
            {
                "device": bucket["device"],
                "mountpoint": ", ".join(sorted(bucket["mounts"]))
                or bucket["device"],
                "fstype": ", ".join(sorted(bucket["fstypes"])),
                "total": total,
                "used": used,
                "percent": percent,
            }
        )

    if not disks:
        try:
            usage = psutil.disk_usage("/")
        except (PermissionError, FileNotFoundError, OSError):
            return disks
        disks.append(
            {
                "device": "/",
                "mountpoint": "/",
                "fstype": "",
                "total": usage.total,
                "used": usage.used,
                "percent": usage.percent,
            }
        )

    return sorted(disks, key=lambda item: item["device"])


@app.route("/api/system")
def system_info():
    """Expose basic system metrics for the dashboard."""
    mem = psutil.virtual_memory()
    uptime_seconds = max(0, time.time() - psutil.boot_time())
    disks = _disk_usage_all()
    payload = {
        "cpu": {
            "usage_percent": psutil.cpu_percent(interval=None),
            "temperature_c": _cpu_temperature_c(),
        },
        "memory": {
            "total": mem.total,
            "used": mem.used,
            "percent": mem.percent,
        },
        "disks": disks,
        "uptime_seconds": uptime_seconds,
    }
    return jsonify(payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
