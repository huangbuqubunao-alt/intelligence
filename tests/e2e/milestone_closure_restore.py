"""Real isolated HTTP archive/restart acceptance; run stage then verify."""

import argparse
import hashlib
import io
import json
import sqlite3
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2] / ".var" / "closure" / "unified"
BASE = "http://127.0.0.1:5492/api/v1/"


def request(path, data=None, *, raw=False):
    headers = {"X-YIA-Request": "local-ui"}
    if isinstance(data, bytes):
        headers["Content-Type"] = "application/zip"
    elif data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    with urlopen(Request(BASE + path, data=data, headers=headers), timeout=20) as response:
        content = response.read()
        return content if raw else json.loads(content)


def snapshot(info):
    rid = info["research_id"]
    pages, cursor = [], None
    while True:
        page = request(f"research/{rid}/history" + (f"?cursor={cursor}" if cursor else ""))
        pages.append(page)
        cursor = page["next_cursor"]
        if not cursor:
            break
    revisions = {identity: request(f"research/{rid}/history/{identity}") for identity in info["revisions"]}
    return {
        "content": request(f"videos/{info['content_id']}"),
        "evidence": request(f"videos/{info['content_id']}/evidence"),
        "da": request(f"videos/{info['content_id']}/deep-analysis"),
        "research": request(f"research/{rid}"), "history": pages, "revisions": revisions,
        "diff": request(f"research/{rid}/diff?base_revision={info['revisions'][0]}&target_revision={info['revisions'][2]}"),
        "delta": request("knowledge-delta"),
        "settings": request("settings"),
        "source_policy": request("settings/source-policy"),
        "sources": request("sources"),
    }


def stage(info):
    before = snapshot(info)
    assert before["da"]["deep_analysis"]["result"]["evidence_citation_status"] == "DURABLE_EVIDENCE_VERIFIED"
    assert len(before["revisions"]) >= 3
    with sqlite3.connect(ROOT / "state.sqlite3") as db:
        dump = "\n".join(db.iterdump())
        authority_hash = hashlib.sha256(dump.encode()).hexdigest()
    try:
        request("backup-restore/restore/stage", b"corrupt archive")
        raise AssertionError("Corrupt archive accepted")
    except HTTPError as error:
        assert error.code == 409, error.code
        assert json.load(error)["error"]["code"] == "BACKUP_RESTORE_REJECTED"
    with sqlite3.connect(ROOT / "state.sqlite3") as db:
        assert hashlib.sha256("\n".join(db.iterdump()).encode()).hexdigest() == authority_hash
    assert snapshot(info) == before
    backup = request("backup-restore/backups", {})["backup"]
    archive = request(f"backup-restore/backups/{backup['backup_id']}/download", raw=True)
    with ZipFile(io.BytesIO(archive)) as zipped:
        names = zipped.namelist()
        assert not any("external-vault" in name or "knowledge-delta" in name or "research-diff" in name for name in names)
    staged = request("backup-restore/restore/stage", archive)["restore"]
    confirmed = request("backup-restore/restore/confirm", {"restore_id": staged["restore_id"]})
    (ROOT / "restore-expected.json").write_text(json.dumps(before, indent=2))
    (ROOT / "restore-stage.json").write_text(json.dumps({"corrupt_rejected_live_unchanged": True, "archive_members": names, "archive_sha256": hashlib.sha256(archive).hexdigest(), "confirmed": confirmed}, indent=2))
    print("Real archive staged and confirmed; corrupt archive rejected without live mutation. Restart isolated server.")


def verify(info):
    expected = json.loads((ROOT / "restore-expected.json").read_text())
    actual = snapshot(info)
    assert actual == expected
    published = request(f"videos/{info['content_id']}/deep-analysis/obsidian", {"result_identity": info["da"]})
    with sqlite3.connect(ROOT / "state.sqlite3") as db:
        checks = {key: db.execute(f"PRAGMA {key}").fetchall() for key in ("quick_check", "integrity_check", "foreign_key_check")}
    assert checks == {"quick_check": [("ok",)], "integrity_check": [("ok",)], "foreign_key_check": []}
    (ROOT / "restore-report.json").write_text(json.dumps({"exact_snapshot": True, "trusted_da": True, "durable_evidence": True, "research_current_history_revisions": True, "settings_source_policy_following": True, "diff_recomputed": True, "delta_recomputed": True, "obsidian_republish": published, "database_checks": checks}, indent=2))
    print("Real archive + restart restores exact DA/Evidence, current/history/revisions; Diff/Delta recompute and Obsidian republishes. Database checks pass.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("stage", "verify"))
    args = parser.parse_args()
    info = json.loads((ROOT / "fixture.json").read_text())
    (stage if args.mode == "stage" else verify)(info)
