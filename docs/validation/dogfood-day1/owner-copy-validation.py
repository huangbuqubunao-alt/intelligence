"""Validate normal startup/migration on the preserved COPY, never real owner DB."""
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path

from youtube_intel.config import load_app_config
from youtube_intel.runtime_composition import build_local_source_run_runtime

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / ".var/dogfood-day1/owner-copy/state.sqlite3"
DEST = Path(tempfile.mkdtemp(prefix="owner-startup-copy-", dir=ROOT / ".var/dogfood-day1"))
assert SNAPSHOT != ROOT.parent / "v1x-local-main/.var/owner/state.sqlite3"
DEST.mkdir(exist_ok=True)
for directory in ("config", "data", "logs", "vault"):
    (DEST / directory).mkdir(exist_ok=True)
for name in ("settings.yaml", "channels.yaml"):
    shutil.copy2(ROOT / ".var/dogfood-day1/live-final/config" / name, DEST / "config" / name)
DB = DEST / "state.sqlite3"
assert not DB.exists(), "Use a fresh validation destination without overwriting evidence"
with sqlite3.connect(f"file:{SNAPSHOT}?mode=ro", uri=True) as source, sqlite3.connect(DB) as target:
    assert source.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert source.execute("PRAGMA user_version").fetchone()[0] == 34
    source.backup(target)

def snapshot():
    with sqlite3.connect(DB) as db:
        db.row_factory = sqlite3.Row
        rows = [dict(row) for row in db.execute("SELECT * FROM source_subscriptions")]
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        counts = {table: db.execute('SELECT COUNT(*) FROM "'+table+'"').fetchone()[0] for table in tables}
        return {"schema":db.execute("PRAGMA user_version").fetchone()[0],"integrity":db.execute("PRAGMA integrity_check").fetchone()[0],"sources":rows,"counts":counts}
before = snapshot()
class NoCredentials:
    def get(self): return None
    def save(self, value): raise AssertionError("Read-only validation")
    def delete(self): raise AssertionError("Read-only validation")
runtime = build_local_source_run_runtime(config=load_app_config(DEST / "config/channels.yaml", DEST / "config/settings.yaml"), project_root=DEST, database=DB, credential_store=NoCredentials())
status, projection = runtime.application.handle("GET", "/api/v1/sources")
after = snapshot()
assert status == 200 and after["schema"] == 35 and after["integrity"] == "ok"
assert before["sources"] == after["sources"], "No historical Source rewrite"
assert len(after["sources"]) == 1
assert projection["sources"][0]["friendly_name"] == "@lingdujieshuo"
assert projection["sources"][0]["needs_attention"] is True
for table in before["counts"]:
    if table != "schema_migrations":
        assert before["counts"][table] == after["counts"][table], table
assert after["counts"]["source_tracking_state"] == 0
assert runtime.repository.list_videos() == ()
assert runtime.repository.list_topics() == ()
Path(__file__).with_name("owner-copy-validation.json").write_text(json.dumps({"runtime_root":str(DEST),"before":before,"after":after,"ui_projection":projection,"normal_supported_composition":True,"historical_source_unchanged":True,"no_silent_conversion":True},ensure_ascii=False,indent=2)+"\n")
print("Owner COPY integrity preserved; supported startup34→35; historical unresolved Source unchanged and visibly needs attention; no data loss")
