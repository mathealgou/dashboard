# Dashboard Flask Server

A lightweight Flask dashboard that pings a small set of personal services and shows their health in `dashboard.html`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask requests psutil
```

## Run

```bash
flask --app app run --host 0.0.0.0 --port 5000 --debug
# or simply
./run.sh
```

Open http://127.0.0.1:5000/ to view the dashboard, which refreshes each service's status every three seconds. System metrics are exposed at `/api/system` for CPU, memory, disk, uptime, and temperature.
