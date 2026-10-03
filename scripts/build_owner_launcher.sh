#!/bin/sh
set -eu
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
APP_ROOT="$PROJECT_ROOT/.var/Intelligence.app"
mkdir -p "$PROJECT_ROOT/.var"
/usr/bin/osacompile -o "$APP_ROOT" \
  -e 'set action to button returned of (display dialog "Intelligence — local candidate / 本地候选" buttons {"Stop / 停止", "Obsidian", "Open / 打开"} default button "Open / 打开")' \
  -e 'set extra to ""' \
  -e 'if action is "Stop / 停止" then set extra to " --stop"' \
  -e 'if action is "Obsidian" then set extra to " --choose-vault"' \
  -e "do shell script quoted form of \"$PROJECT_ROOT/.venv/bin/python\" & \" \" & quoted form of \"$PROJECT_ROOT/scripts/owner_launcher.py\" & extra"
echo "$APP_ROOT"
