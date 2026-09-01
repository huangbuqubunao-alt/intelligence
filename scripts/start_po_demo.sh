#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
RUNTIME_ROOT="$PROJECT_ROOT/.var/po-demo"
STATE_ROOT="$RUNTIME_ROOT/state"
API_PID_FILE="$STATE_ROOT/api.pid"
FRONTEND_PID_FILE="$STATE_ROOT/frontend.pid"
PYTHON="$PROJECT_ROOT/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
  echo "Missing project virtual environment: $PYTHON" >&2
  exit 1
fi

if [ -f "$API_PID_FILE" ] || [ -f "$FRONTEND_PID_FILE" ]; then
  echo "PO demo state already exists. Run ./scripts/stop_po_demo.sh first." >&2
  exit 1
fi

"$PYTHON" -m youtube_intel.po_demo prepare --project-root "$PROJECT_ROOT" >/dev/null
mkdir -p "$STATE_ROOT/logs"

(
  cd "$PROJECT_ROOT"
  exec nohup "$PYTHON" -m youtube_intel.po_demo serve --project-root "$PROJECT_ROOT" --port 8765
) >"$STATE_ROOT/logs/api.log" 2>&1 &
echo "$!" >"$API_PID_FILE"

(
  cd "$PROJECT_ROOT/frontend"
  exec nohup "$PROJECT_ROOT/frontend/node_modules/.bin/vite" --host 127.0.0.1 --port 5173 --strictPort
) >"$STATE_ROOT/logs/frontend.log" 2>&1 &
echo "$!" >"$FRONTEND_PID_FILE"

for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8765/api/v1/system >/dev/null 2>&1 && curl -fsS http://127.0.0.1:5173/ >/dev/null 2>&1; then
    echo "PO Review Demo is ready at http://127.0.0.1:5173/"
    break
  fi
  sleep 1
done
if ! curl -fsS http://127.0.0.1:8765/api/v1/system >/dev/null 2>&1 || ! curl -fsS http://127.0.0.1:5173/ >/dev/null 2>&1; then
  echo "PO demo did not become ready; inspect $STATE_ROOT/logs/." >&2
  exit 1
fi
echo "Runtime: $RUNTIME_ROOT"
