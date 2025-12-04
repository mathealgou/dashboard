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


@app.route("/api/system")
def system_info():
    """Expose basic system metrics for the dashboard."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    uptime_seconds = max(0, time.time() - psutil.boot_time())
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
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "percent": disk.percent,
        },
        "uptime_seconds": uptime_seconds,
    }
    return jsonify(payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
