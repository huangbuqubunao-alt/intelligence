#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
PYTHON="$PROJECT_ROOT/.venv/bin/python"
"$PROJECT_ROOT/scripts/stop_po_demo.sh"
"$PYTHON" -m youtube_intel.po_demo reset --project-root "$PROJECT_ROOT" >/dev/null
echo "PO demo runtime reset: $PROJECT_ROOT/.var/po-demo"
