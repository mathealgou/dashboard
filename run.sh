#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

VENV_DIR="$ROOT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

REQUIRED_MODULES=(flask requests psutil)

for module in "${REQUIRED_MODULES[@]}"; do
    if ! python -c "import ${module}" >/dev/null 2>&1; then
        pip install "${module}"
    fi
done

exec flask --app app run --host 0.0.0.0 --port 5000 --debug
