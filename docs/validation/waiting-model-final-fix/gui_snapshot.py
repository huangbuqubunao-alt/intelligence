"""Read only the isolated acceptance DB/DATA; refuse any other path."""
import hashlib
import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / (
    ".var/waiting-model-final-fix/gui-final" if os.environ.get("WAITING_MODEL_FINAL_GUI") == "1"
    else ".var/waiting-model-final-fix/gui"
)
with sqlite3.connect(f"{(ROOT / 'state.sqlite3').as_uri()}?mode=ro", uri=True) as connection:
    tables = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    rows = {table: sorted([list(r) for r in connection.execute(f'SELECT * FROM "{table}"')], key=lambda r: json.dumps(r)) for table in tables}
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
files = {str(path.relative_to(ROOT / "data")): hashlib.sha256(path.read_bytes()).hexdigest()
         for path in sorted((ROOT / "data").rglob("*")) if path.is_file()}
print(json.dumps({"integrity": integrity, "rows": rows, "files": files}, ensure_ascii=False, sort_keys=True))
