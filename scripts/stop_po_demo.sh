#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
STATE_ROOT="$PROJECT_ROOT/.var/po-demo/state"

stop_owned_pid() {
  pid_file=$1
  if [ ! -f "$pid_file" ]; then
    return
  fi
  pid=$(cat "$pid_file")
  case "$pid" in
    *[!0-9]*|'') echo "Refusing invalid demo pid state: $pid_file" >&2; exit 1 ;;
  esac
  if kill -0 "$pid" 2>/dev/null; then
    command=$(ps -p "$pid" -o command= || true)
    case "$command" in
      *"$PROJECT_ROOT"*) kill "$pid" ;;
      *) echo "Refusing to stop a process not owned by this PO demo: $pid" >&2; exit 1 ;;
    esac
  fi
  rm -f "$pid_file"
}

stop_owned_pid "$STATE_ROOT/frontend.pid"
stop_owned_pid "$STATE_ROOT/api.pid"
echo "PO demo processes stopped. Demo data remains in $PROJECT_ROOT/.var/po-demo."
