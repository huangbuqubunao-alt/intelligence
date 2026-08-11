#!/usr/bin/env bash
# Layered security and leak scanner for Release Candidate validation.
#
# The scanner logic lives in scripts/_security_scan.py (standard-library Python)
# so regex and AST behaviour is identical on macOS and Linux. This shell script
# is a thin fail-closed wrapper.
#
# Usage: bash scripts/security_scan.sh [scan-root]

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f "$ROOT/.venv/bin/python" ]; then
    PYTHON="$ROOT/.venv/bin/python"
else
    PYTHON="python3"
fi

exec "$PYTHON" "$ROOT/scripts/_security_scan.py" "$@"
