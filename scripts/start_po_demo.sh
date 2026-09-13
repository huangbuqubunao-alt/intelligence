#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
RUNTIME_ROOT="$PROJECT_ROOT/.var/po-demo"
STATE_ROOT="$RUNTIME_ROOT/state"
API_PID_FILE="$STATE_ROOT/api.pid"
FRONTEND_PID_FILE="$STATE_ROOT/frontend.pid"
PYTHON="$PROJECT_ROOT/.venv/bin/python"
API_PORT=${YIA_PO_DEMO_API_PORT:-8766}
FRONTEND_PORT=${YIA_PO_DEMO_FRONTEND_PORT:-5174}

case "$API_PORT" in *[!0-9]*|'') echo "Invalid PO demo API port: $API_PORT" >&2; exit 1 ;; esac
case "$FRONTEND_PORT" in *[!0-9]*|'') echo "Invalid PO demo frontend port: $FRONTEND_PORT" >&2; exit 1 ;; esac

if [ ! -x "$PYTHON" ]; then
  echo "Missing project virtual environment: $PYTHON" >&2
  exit 1
fi

loopback_port_is_available() {
  "$PYTHON" - "$1" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
    probe.bind(("127.0.0.1", port))
PY
}

if ! loopback_port_is_available "$API_PORT"; then
  echo "PO demo API port is already in use: $API_PORT" >&2
  exit 1
fi
if ! loopback_port_is_available "$FRONTEND_PORT"; then
  echo "PO demo frontend port is already in use: $FRONTEND_PORT" >&2
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
  exec nohup "$PYTHON" -m youtube_intel.po_demo serve --project-root "$PROJECT_ROOT" --port "$API_PORT"
) >"$STATE_ROOT/logs/api.log" 2>&1 &
echo "$!" >"$API_PID_FILE"
API_PID=$!

(
  cd "$PROJECT_ROOT/frontend"
  exec nohup env "YIA_API_BASE=http://127.0.0.1:$API_PORT" "$PROJECT_ROOT/frontend/node_modules/.bin/vite" --host 127.0.0.1 --port "$FRONTEND_PORT" --strictPort
) >"$STATE_ROOT/logs/frontend.log" 2>&1 &
echo "$!" >"$FRONTEND_PID_FILE"
FRONTEND_PID=$!

for _ in $(seq 1 60); do
  if kill -0 "$API_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null && curl -fsS "http://127.0.0.1:$API_PORT/api/v1/system" >/dev/null 2>&1 && curl -fsS "http://127.0.0.1:$FRONTEND_PORT/" >/dev/null 2>&1; then
    echo "PO Review Demo is ready at http://127.0.0.1:$FRONTEND_PORT/"
    break
  fi
  sleep 1
done
if ! kill -0 "$API_PID" 2>/dev/null || ! kill -0 "$FRONTEND_PID" 2>/dev/null || ! curl -fsS "http://127.0.0.1:$API_PORT/api/v1/system" >/dev/null 2>&1 || ! curl -fsS "http://127.0.0.1:$FRONTEND_PORT/" >/dev/null 2>&1; then
  echo "PO demo did not become ready; inspect $STATE_ROOT/logs/." >&2
  exit 1
fi
echo "Runtime: $RUNTIME_ROOT"
