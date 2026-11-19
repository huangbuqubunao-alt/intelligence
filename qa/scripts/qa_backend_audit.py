"""Comprehensive real-server HTTP API, persistence, concurrency, fault, security, and CLI QA audit."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import statistics
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
QA_ROOT = REPO_ROOT / ".var" / "qa-audit" / "backend-run"
REPORT_PATH = REPO_ROOT / "qa" / "evidence" / "backend-audit-report.json"
API_PORT = 6491
BASE_URL = f"http://127.0.0.1:{API_PORT}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        return None


OPENER = urllib.request.build_opener(NoRedirect())


def http_call(
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    include_ui_header: bool = True,
    timeout: float = 20.0,
) -> tuple[int, dict[str, str], bytes, float]:
    hdrs: dict[str, str] = {}
    if include_ui_header and method not in {"GET", "HEAD"}:
        hdrs["X-YIA-Request"] = "local-ui"
    if body is not None and "Content-Type" not in (headers or {}):
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=hdrs, method=method)
    t0 = time.perf_counter()
    try:
        with OPENER.open(req, timeout=timeout) as resp:
            raw = resp.read()
            dt = (time.perf_counter() - t0) * 1000.0
            return int(resp.status), dict(resp.headers.items()), raw, dt
    except urllib.error.HTTPError as err:
        raw = err.read()
        dt = (time.perf_counter() - t0) * 1000.0
        return int(err.code), dict(err.headers.items()), raw, dt


def json_call(
    method: str,
    path: str,
    payload: object | None = None,
    *,
    raw_body: bytes | None = None,
    headers: dict[str, str] | None = None,
    include_ui_header: bool = True,
    timeout: float = 20.0,
) -> tuple[int, Any, float]:
    body = raw_body
    if body is None and payload is not None:
        body = json.dumps(payload).encode("utf-8")
    elif body is None and method not in {"GET", "HEAD"}:
        body = b"{}"
    status, _hdrs, raw, dt = http_call(
        method,
        path,
        body=body,
        headers=headers,
        include_ui_header=include_ui_header,
        timeout=timeout,
    )
    if not raw:
        return status, None, dt
    try:
        return status, json.loads(raw.decode("utf-8")), dt
    except Exception:
        return status, raw.decode("utf-8", errors="replace"), dt


def prepare_project_dir() -> Path:
    if QA_ROOT.exists():
        shutil.rmtree(QA_ROOT)
    (QA_ROOT / "config").mkdir(parents=True, exist_ok=True)
    for sub in ("data", "logs", "vault", "templates"):
        (QA_ROOT / sub).mkdir(parents=True, exist_ok=True)
    lines = (REPO_ROOT / "config" / "settings.example.yaml").read_text(encoding="utf-8").splitlines()
    out_lines: list[str] = []
    for line in lines:
        if line.strip().startswith("vault_root:"):
            out_lines.append(f"  vault_root: {QA_ROOT / 'vault'}")
        else:
            out_lines.append(line)
    (QA_ROOT / "config" / "settings.yaml").write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    channels_txt = (REPO_ROOT / "config" / "channels.example.yaml").read_text(encoding="utf-8")
    channels_txt = channels_txt.replace("enabled: true", "enabled: false")
    (QA_ROOT / "config" / "channels.yaml").write_text(channels_txt, encoding="utf-8")
    return QA_ROOT


def start_server(project_root: Path, log_path: Path) -> tuple[subprocess.Popen[bytes], float]:
    db_path = project_root / "state.sqlite3"
    python_bin = REPO_ROOT / ".venv" / "bin" / "python"
    if not python_bin.exists():
        python_bin = Path(os.sys.executable)
    log_file = log_path.open("wb")
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        [
            str(python_bin),
            "-m",
            "youtube_intel",
            "--project-root",
            str(project_root),
            "serve-api",
            "--database",
            str(db_path),
            "--port",
            str(API_PORT),
        ],
        cwd=str(REPO_ROOT),
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            log_file.close()
            raise RuntimeError(f"serve-api exited early with {proc.returncode}; see {log_path}")
        try:
            st, data, _ = json_call("GET", "/api/v1/system", timeout=2.0)
            if st == 200 and isinstance(data, dict):
                return proc, (time.perf_counter() - t0) * 1000.0
        except Exception:
            time.sleep(0.15)
    proc.terminate()
    proc.wait(timeout=10)
    log_file.close()
    raise RuntimeError("serve-api health check timed out")


def stop_server(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=12)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def main() -> int:
    report: dict[str, Any] = {
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "base_url": BASE_URL,
        "checks": [],
        "latencies_ms": {},
        "cli": {},
        "sqlite_integrity": {},
        "summary": {"total": 0, "passed": 0, "failed": 0},
    }

    def record(name: str, category: str, passed: bool, detail: dict[str, Any], latency_ms: float | None = None) -> None:
        item: dict[str, Any] = {
            "name": name,
            "category": category,
            "passed": bool(passed),
            "detail": detail,
        }
        if latency_ms is not None:
            item["latency_ms"] = round(latency_ms, 2)
        report["checks"].append(item)
        report["summary"]["total"] += 1
        if passed:
            report["summary"]["passed"] += 1
        else:
            report["summary"]["failed"] += 1

    project_root = prepare_project_dir()
    log1 = REPO_ROOT / "qa" / "evidence" / "backend-server-run1.log"
    log2 = REPO_ROOT / "qa" / "evidence" / "backend-server-run2.log"
    proc: subprocess.Popen[bytes] | None = None

    try:
        proc, boot_ms = start_server(project_root, log1)
        record("server_boot_and_system_health", "boot", True, {"boot_ms": round(boot_ms, 1)}, boot_ms)

        # 1. Read Surface & Latencies
        get_routes = [
            "/api/v1/system",
            "/api/v1/dashboard",
            "/api/v1/knowledge-delta",
            "/api/v1/activity",
            "/api/v1/settings",
            "/api/v1/sources",
            "/api/v1/videos",
            "/api/v1/intelligence",
            "/api/v1/saved-intelligence",
            "/api/v1/topics",
            "/api/v1/research",
            "/api/v1/research/capability",
            "/api/v1/research/scope",
            "/api/v1/backup-restore/status",
            "/api/v1/deep-analysis/capability",
            "/api/v1/cloud-intelligence/profiles",
            "/api/v1/local/native/capability",
            "/api/v1/local/transcription/capability",
            "/api/v1/workspace-ai/settings",
            "/api/v1/workspace-ai/sync-status",
            "/api/v1/workspace-ai/weekly-brief",
            "/api/v1/workspace-ai/research/sessions",
            "/api/v1/workspace-ai/backup",
            "/api/v1/workspace-ai/obsidian-bundle",
        ]
        all_latencies: list[float] = []
        for route in get_routes:
            st, body, dt = json_call("GET", route)
            all_latencies.append(dt)
            ok = st == 200 and isinstance(body, dict)
            # Measure warm hit too
            st2, _b2, dt2 = json_call("GET", route)
            all_latencies.append(dt2)
            record(
                f"get_{route}",
                "read_surface",
                ok and st2 == 200,
                {"cold_status": st, "warm_status": st2, "cold_ms": round(dt, 2), "warm_ms": round(dt2, 2)},
                dt,
            )

        # ZIP obsidian bundle endpoint
        st_zip, hdrs_zip, raw_zip, dt_zip = http_call("GET", "/api/v1/workspace-ai/obsidian-bundle.zip")
        zip_valid = False
        if st_zip == 200 and raw_zip[:2] == b"PK":
            with zipfile.ZipFile(BytesIO(raw_zip)) as zf:
                zip_valid = zf.testzip() is None
        record(
            "get_obsidian_bundle_zip",
            "read_surface",
            st_zip == 200 and zip_valid,
            {"status": st_zip, "bytes": len(raw_zip), "content_type": hdrs_zip.get("Content-Type"), "zip_valid": zip_valid},
            dt_zip,
        )

        # 2. Security Boundaries & Redaction
        st_no_hdr, b_no_hdr, dt = json_call("POST", "/api/v1/topics", {"command_id": "sec-1", "name": "x"}, include_ui_header=False)
        record("reject_mutation_without_ui_header", "security", st_no_hdr == 403, {"status": st_no_hdr, "body": b_no_hdr}, dt)

        st_bad_org, b_bad_org, dt = json_call(
            "POST",
            "/api/v1/topics",
            {"command_id": "sec-2", "name": "x"},
            headers={"Origin": "https://evil.example"},
        )
        record("reject_mutation_evil_origin", "security", st_bad_org == 403, {"status": st_bad_org, "body": b_bad_org}, dt)

        st_nat, b_nat, dt = json_call(
            "POST",
            "/api/v1/local/native/picks",
            {},
            headers={"Origin": "https://evil.example"},
        )
        record("native_route_rejects_evil_origin_or_unavailable", "security", st_nat in {403, 404}, {"status": st_nat, "body": b_nat}, dt)

        _, settings_body, _ = json_call("GET", "/api/v1/settings")
        _, ws_settings_body, _ = json_call("GET", "/api/v1/workspace-ai/settings")
        settings_dump = json.dumps({"s": settings_body, "ws": ws_settings_body})
        no_secret_leak = ("sk-" not in settings_dump) and ("api_key_value" not in settings_dump)
        record("settings_redaction_no_raw_secrets", "security", no_secret_leak, {"cloud_credential": (settings_body or {}).get("cloud_credential")})

        # 3. Validation, Injection, Traversal, Error Handling
        st_mal, b_mal, dt = json_call("POST", "/api/v1/topics", raw_body=b"{broken")
        record("malformed_json_returns_4xx", "validation", 400 <= st_mal < 500, {"status": st_mal, "body": b_mal}, dt)

        st_404, b_404, dt = json_call("GET", "/api/v1/nonexistent-qa-route")
        record("unknown_route_404", "validation", st_404 == 404, {"status": st_404, "body": b_404}, dt)

        st_v404, b_v404, dt = json_call("GET", "/api/v1/videos/does-not-exist-qa-999")
        record("missing_video_404", "validation", st_v404 == 404, {"status": st_v404, "body": b_v404}, dt)

        st_m405, b_m405, dt = json_call("DELETE", "/api/v1/settings", raw_body=b"")
        record("wrong_method_settings_4xx", "validation", 400 <= st_m405 < 500, {"status": st_m405, "body": b_m405}, dt)

        st_lang_bad, b_lang_bad, dt = json_call("PUT", "/api/v1/settings/output-language", {"output_language": "fr"})
        record("invalid_output_language_422", "validation", st_lang_bad == 422, {"status": st_lang_bad, "body": b_lang_bad}, dt)

        st_trav, b_trav, dt = json_call(
            "POST",
            "/api/v1/local/imports?filename=..%2F..%2Fetc%2Fpasswd.txt",
            raw_body=b"hello traversal guard",
            headers={"Content-Type": "application/octet-stream"},
        )
        trav_fname = (b_trav or {}).get("import", {}).get("filename") if isinstance(b_trav, dict) else None
        st_trav_bad, b_trav_bad, _ = json_call(
            "POST",
            "/api/v1/local/imports?filename=..%2F..",
            raw_body=b"hello",
            headers={"Content-Type": "application/octet-stream"},
        )
        record(
            "import_path_traversal_neutralized_or_rejected",
            "security",
            st_trav == 201 and trav_fname == "passwd.txt" and st_trav_bad == 422,
            {"traversal_txt_status": st_trav, "sanitized_filename": trav_fname, "dotdot_status": st_trav_bad, "dotdot_body": b_trav_bad},
            dt,
        )

        # 4. Local Import Lifecycle & DB verification
        sample_txt = b"QA Verification Note\n\nDeterministic state machines prevent silent corruption.\n\nOffline local imports keep data private.\n"
        st_ct_415, b_ct_415, dt_415 = json_call(
            "POST",
            "/api/v1/local/imports?filename=qa-note.txt",
            raw_body=sample_txt,
            headers={"Content-Type": "text/plain"},
        )
        record("local_import_requires_octet_stream_415", "validation", st_ct_415 == 415, {"status": st_ct_415, "body": b_ct_415}, dt_415)

        st_imp, b_imp, dt = json_call(
            "POST",
            "/api/v1/local/imports?filename=qa-note.txt",
            raw_body=sample_txt,
            headers={"Content-Type": "application/octet-stream"},
        )
        cid_txt = (b_imp or {}).get("import", {}).get("content_id") if isinstance(b_imp, dict) else None
        record("local_import_valid_txt", "import", st_imp == 201 and bool(cid_txt), {"status": st_imp, "body": b_imp}, dt)

        st_dup, b_dup, dt = json_call(
            "POST",
            "/api/v1/local/imports?filename=qa-note.txt",
            raw_body=sample_txt,
            headers={"Content-Type": "application/octet-stream"},
        )
        dup_flag = (b_dup or {}).get("import", {}).get("duplicate") if isinstance(b_dup, dict) else None
        dup_cid = (b_dup or {}).get("import", {}).get("content_id") if isinstance(b_dup, dict) else None
        record("local_import_duplicate_idempotent", "import", st_dup == 200 and dup_flag is True and dup_cid == cid_txt, {"status": st_dup, "body": b_dup}, dt)

        sample_md = b"# QA Markdown Architecture\n\n- Evidence spans stay traceable.\n- Reload must persist everything.\n"
        st_md, b_md, dt = json_call(
            "POST",
            "/api/v1/local/imports?filename=qa-doc.md",
            raw_body=sample_md,
            headers={"Content-Type": "application/octet-stream"},
        )
        cid_md = (b_md or {}).get("import", {}).get("content_id") if isinstance(b_md, dict) else None
        record("local_import_valid_md", "import", st_md == 201 and bool(cid_md), {"status": st_md, "body": b_md}, dt)

        st_empty, b_empty, dt = json_call(
            "POST",
            "/api/v1/local/imports?filename=empty.txt",
            raw_body=b"",
            headers={"Content-Type": "application/octet-stream"},
        )
        record("local_import_reject_empty", "import", st_empty == 422, {"status": st_empty, "body": b_empty}, dt)

        st_exe, b_exe, dt = json_call(
            "POST",
            "/api/v1/local/imports?filename=bad.exe",
            raw_body=b"MZ\x90\x00",
            headers={"Content-Type": "application/octet-stream"},
        )
        record("local_import_reject_exe", "import", st_exe == 422, {"status": st_exe, "body": b_exe}, dt)

        st_utf8, b_utf8, dt = json_call(
            "POST",
            "/api/v1/local/imports?filename=bad-utf8.txt",
            raw_body=b"\xff\xfe\xfd\x80\x81",
            headers={"Content-Type": "application/octet-stream"},
        )
        record("local_import_reject_invalid_utf8", "import", st_utf8 == 422, {"status": st_utf8, "body": b_utf8}, dt)

        if cid_txt:
            st_vd, b_vd, dt = json_call("GET", f"/api/v1/videos/{cid_txt}")
            st_ev, b_ev, dt2 = json_call("GET", f"/api/v1/videos/{cid_txt}/evidence")
            record(
                "imported_video_and_evidence_readable",
                "import",
                st_vd == 200 and st_ev == 200 and bool((b_ev or {}).get("evidence")),
                {"video_status": st_vd, "evidence_status": st_ev, "evidence_count": len((b_ev or {}).get("evidence", []))},
                dt + dt2,
            )

        # 5. Settings, Preferences, Topics (with XSS/SQLi literal tests), Curation, Research
        st_lang_en, b_lang_en, dt = json_call("PUT", "/api/v1/settings/output-language", {"output_language": "en"})
        st_lang_zh, b_lang_zh, _ = json_call("PUT", "/api/v1/settings/output-language", {"output_language": "zh-CN"})
        record(
            "output_language_roundtrip",
            "settings",
            st_lang_en == 200 and (b_lang_en or {}).get("output_language") == "en" and st_lang_zh == 200 and (b_lang_zh or {}).get("output_language") == "zh-CN",
            {"en_status": st_lang_en, "zh_status": st_lang_zh},
            dt,
        )

        st_pref, b_pref, dt = json_call(
            "POST",
            "/api/v1/settings/preferences/long-term",
            {"command_id": "qa-pref-1", "scope": "GLOBAL_CONTENT", "target_id": None, "statement": "Focus on agent architecture"},
        )
        pref_id = (b_pref or {}).get("preference", {}).get("preference_id") if isinstance(b_pref, dict) else None
        st_pref_patch, b_pref_patch, _ = json_call(
            "PATCH",
            f"/api/v1/settings/preferences/{pref_id}",
            {"command_id": "qa-pref-patch-1", "statement": "Focus on agent reliability"},
        ) if pref_id else (0, None, 0.0)
        record(
            "preferences_create_and_patch",
            "settings",
            st_pref == 201 and st_pref_patch == 200,
            {"create_status": st_pref, "patch_status": st_pref_patch, "pref_id": pref_id, "body": b_pref},
            dt,
        )

        xss_sqli_name = "QA Topic ' OR 1=1 -- <script>alert(1)</script>"
        st_top, b_top, dt = json_call("POST", "/api/v1/topics", {"command_id": "qa-top-1", "name": xss_sqli_name})
        topic_id = (b_top or {}).get("topic", {}).get("topic_id") if isinstance(b_top, dict) else None
        st_top_rename, b_top_rename, _ = json_call("PATCH", f"/api/v1/topics/{topic_id}", {"name": "QA Benchmark Topic"}) if topic_id else (0, None, 0.0)
        st_top_pin, b_top_pin, _ = json_call("POST", f"/api/v1/topics/{topic_id}/pin", {"pinned": True}) if topic_id else (0, None, 0.0)
        record(
            "topics_crud_and_sqli_xss_literal_safety",
            "topics",
            st_top == 201 and st_top_rename == 200 and st_top_pin == 200 and (b_top or {}).get("topic", {}).get("name") == xss_sqli_name,
            {"create": st_top, "rename": st_top_rename, "pin": st_top_pin, "topic_id": topic_id},
            dt,
        )

        # Spending policy optimistic concurrency conflict
        st_pol, b_pol, dt = json_call(
            "PUT",
            "/api/v1/settings/cloud-spending-policy",
            {
                "expected_revision": 999,
                "enabled": False,
                "total_cny": "0",
                "per_request_cny": "0",
                "max_calls": 0,
                "accept_price_hash": "",
                "acknowledge": False,
            },
        )
        record("spending_policy_stale_revision_conflict", "settings", st_pol in {409, 422}, {"status": st_pol, "body": b_pol}, dt)

        # Research build + invalid checks
        research_id = None
        if cid_txt:
            st_res, b_res, dt = json_call(
                "POST",
                "/api/v1/research",
                {"question": "What keeps local data private?", "content_ids": [cid_txt]},
            )
            res_obj = (b_res or {}).get("research", {}) if isinstance(b_res, dict) else {}
            research_id = res_obj.get("research_id") or (res_obj.get("packet") or {}).get("research_id")
            st_res_get, _, _ = json_call("GET", f"/api/v1/research/{research_id}") if research_id else (0, None, 0.0)
            st_res_bad_q, _, _ = json_call("POST", "/api/v1/research", {"question": "   ", "content_ids": [cid_txt]})
            st_res_empty_s, _, _ = json_call("POST", "/api/v1/research", {"question": "valid?", "content_ids": []})
            record(
                "research_create_read_and_invalid_rejects",
                "research",
                st_res == 201 and st_res_get == 200 and st_res_bad_q == 422 and st_res_empty_s == 422,
                {"create": st_res, "read": st_res_get, "blank_q": st_res_bad_q, "empty_scope": st_res_empty_s, "research_id": research_id},
                dt,
            )

        # Workspace-AI curation & ask boundary (must not 500)
        if cid_txt:
            st_cur, b_cur, dt = json_call(
                "POST",
                f"/api/v1/workspace-ai/videos/{cid_txt}/curation",
                {"starred": True, "is_read": True},
            )
            st_ask_empty, _b_ask_empty, _ = json_call("POST", "/api/v1/workspace-ai/research/ask", {"question": ""})
            st_ask_valid, b_ask_valid, _ = json_call(
                "POST",
                "/api/v1/workspace-ai/research/ask",
                {"question": "What is verified here?", "video_ids": [cid_txt]},
            )
            record(
                "workspace_ai_curation_and_ask_validation",
                "workspace_ai",
                st_cur == 200 and st_ask_empty == 422 and st_ask_valid < 500,
                {"curation_status": st_cur, "ask_empty_status": st_ask_empty, "ask_valid_status": st_ask_valid, "ask_valid": b_ask_valid},
                dt,
            )

        # 6. Backup & Restore Fault Injection
        st_bk, b_bk, dt = json_call("POST", "/api/v1/backup-restore/backups", {})
        backup_id = (b_bk or {}).get("backup", {}).get("backup_id") if isinstance(b_bk, dict) else None
        st_dl, _, raw_dl, dt_dl = http_call("GET", f"/api/v1/backup-restore/backups/{backup_id}/download") if backup_id else (0, {}, b"", 0.0)
        bk_zip_ok = False
        if st_dl == 200 and raw_dl[:2] == b"PK":
            with zipfile.ZipFile(BytesIO(raw_dl)) as zf:
                bk_zip_ok = zf.testzip() is None
        st_corrupt, b_corrupt, dt_c = json_call(
            "POST",
            "/api/v1/backup-restore/restore/stage",
            raw_body=b"CORRUPT_NOT_A_ZIP_BYTES",
            headers={"Content-Type": "application/zip"},
        )
        st_stage, b_stage, dt_s = json_call(
            "POST",
            "/api/v1/backup-restore/restore/stage",
            raw_body=raw_dl if bk_zip_ok else b"",
            headers={"Content-Type": "application/zip"},
        )
        restore_id = (b_stage or {}).get("restore", {}).get("restore_id") if isinstance(b_stage, dict) else None
        st_cancel, b_cancel, _ = json_call("POST", "/api/v1/backup-restore/restore/cancel", {"restore_id": restore_id}) if restore_id else (0, None, 0.0)
        record(
            "backup_download_corrupt_reject_stage_cancel",
            "backup_restore",
            st_bk == 201 and st_dl == 200 and bk_zip_ok and (400 <= st_corrupt < 500) and st_stage == 200 and st_cancel == 200,
            {
                "backup_status": st_bk,
                "download_status": st_dl,
                "backup_bytes": len(raw_dl),
                "zip_valid": bk_zip_ok,
                "corrupt_stage_status": st_corrupt,
                "valid_stage_status": st_stage,
                "cancel_status": st_cancel,
            },
            dt + dt_dl + dt_c + dt_s,
        )

        # 7. Process Restart Persistence
        stop_server(proc)
        proc = None
        proc, boot2_ms = start_server(project_root, log2)
        st_vid_after, b_vid_after, _ = json_call("GET", "/api/v1/videos")
        st_top_after, b_top_after, _ = json_call("GET", "/api/v1/topics")
        st_res_after, b_res_after, _ = json_call("GET", "/api/v1/research")
        vids = {v.get("video_id") for v in (b_vid_after or {}).get("videos", []) if isinstance(v, dict)}
        topics_map = {t.get("topic_id"): t for t in (b_top_after or {}).get("topics", []) if isinstance(t, dict)}
        res_list = (b_res_after or {}).get("research", []) if isinstance(b_res_after, dict) else []
        res_ids = {
            (r.get("research_id") or (r.get("packet") or {}).get("research_id"))
            for r in res_list
            if isinstance(r, dict)
        }
        # Inspect actual /api/v1/research shape safely
        persisted_ok = (
            st_vid_after == 200
            and st_top_after == 200
            and st_res_after == 200
            and (cid_txt in vids if cid_txt else False)
            and (cid_md in vids if cid_md else False)
            and (research_id in res_ids if research_id else False)
            and (topic_id in topics_map and topics_map[topic_id].get("name") == "QA Benchmark Topic" and topics_map[topic_id].get("pinned") is True if topic_id else False)
        )
        record(
            "restart_persistence_videos_topics_research",
            "persistence",
            persisted_ok,
            {
                "boot2_ms": round(boot2_ms, 1),
                "videos_count": len(vids),
                "topic_persisted": topics_map.get(topic_id) if topic_id else None,
                "research_persisted": (research_id in res_ids if research_id else False),
            },
            boot2_ms,
        )

        # 8. Concurrency Wave (20 threads, 80 mixed requests, zero 500s / lock errors)
        def worker(idx: int) -> tuple[int, str, float]:
            mode = idx % 5
            if mode == 0:
                st, _b, dt = json_call("GET", "/api/v1/videos")
                return st, "GET /videos", dt
            if mode == 1:
                st, _b, dt = json_call("GET", "/api/v1/dashboard")
                return st, "GET /dashboard", dt
            if mode == 2:
                st, _b, dt = json_call("GET", "/api/v1/intelligence")
                return st, "GET /intelligence", dt
            if mode == 3:
                st, _b, dt = json_call("POST", "/api/v1/sources/check-stale", {})
                return st, "POST /sources/check-stale", dt
            st, _b, dt = json_call(
                "POST",
                "/api/v1/local/imports?filename=qa-note.txt",
                raw_body=sample_txt,
                headers={"Content-Type": "application/octet-stream"},
            )
            return st, "POST /local/imports(dup)", dt

        conc_results: list[tuple[int, str, float]] = []
        conc_errors: list[str] = []
        with ThreadPoolExecutor(max_workers=20) as pool:
            futs = [pool.submit(worker, i) for i in range(80)]
            for fut in as_completed(futs):
                try:
                    conc_results.append(fut.result())
                except Exception as exc:
                    conc_errors.append(repr(exc))
        server_5xx = [r for r in conc_results if r[0] >= 500]
        unexpected_status = [r for r in conc_results if r[0] not in {200, 201, 202, 409, 429}]
        conc_dts = [r[2] for r in conc_results]
        record(
            "concurrency_20threads_80requests",
            "concurrency",
            len(conc_errors) == 0 and len(server_5xx) == 0 and len(unexpected_status) == 0,
            {
                "completed": len(conc_results),
                "exceptions": conc_errors,
                "server_5xx": len(server_5xx),
                "unexpected_status": unexpected_status[:10],
                "p50_ms": round(statistics.median(conc_dts), 2) if conc_dts else None,
                "p95_ms": round(sorted(conc_dts)[int(0.95 * len(conc_dts)) - 1], 2) if conc_dts else None,
            },
        )
    finally:
        stop_server(proc)

    # 9. SQLite Direct Integrity Checks
    sqlite_files = [project_root / "state.sqlite3"]
    for extra in project_root.rglob("*.sqlite3"):
        if extra not in sqlite_files:
            sqlite_files.append(extra)
    all_db_ok = True
    for dbp in sqlite_files:
        conn = sqlite3.connect(str(dbp))
        try:
            ic = [r[0] for r in conn.execute("PRAGMA integrity_check").fetchall()]
            fk = conn.execute("PRAGMA foreign_key_check").fetchall()
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            row_counts: dict[str, int] = {}
            for tbl in ("videos", "evidence", "artifacts", "topics", "preferences"):
                if tbl in tables:
                    row_counts[tbl] = int(conn.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0])
            ok = ic == ["ok"] and fk == []
            if not ok:
                all_db_ok = False
            report["sqlite_integrity"][str(dbp.relative_to(project_root))] = {
                "integrity_check": ic,
                "foreign_key_check": fk,
                "row_counts": row_counts,
                "ok": ok,
            }
        finally:
            conn.close()
    record("sqlite_integrity_and_fk_check", "database", all_db_ok and len(sqlite_files) >= 1, report["sqlite_integrity"])

    # 10. CLI doctor audit (uninitialized empty dir vs initialized QA dir)
    python_bin = REPO_ROOT / ".venv" / "bin" / "python"
    if not python_bin.exists():
        python_bin = Path(os.sys.executable)
    with tempfile.TemporaryDirectory() as empty_dir:
        doc_empty = subprocess.run(
            [str(python_bin), "-m", "youtube_intel", "--project-root", empty_dir, "doctor"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=20,
        )
        doc_qa = subprocess.run(
            [str(python_bin), "-m", "youtube_intel", "--project-root", str(project_root), "doctor"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=20,
        )
        report["cli"] = {
            "doctor_uninitialized": {
                "returncode": doc_empty.returncode,
                "stdout": doc_empty.stdout[:1200],
                "stderr": doc_empty.stderr[:1200],
            },
            "doctor_initialized_qa": {
                "returncode": doc_qa.returncode,
                "stdout": doc_qa.stdout[:2000],
                "stderr": doc_qa.stderr[:1200],
            },
        }
        record(
            "cli_doctor_safe_handling",
            "cli",
            doc_empty.returncode != 0 and doc_qa.returncode in {0, 1, 2, 3, 4},
            {
                "empty_rc": doc_empty.returncode,
                "qa_rc": doc_qa.returncode,
            },
        )

    if all_latencies:
        s_lats = sorted(all_latencies)
        report["latencies_ms"] = {
            "samples": len(s_lats),
            "p50_ms": round(statistics.median(s_lats), 2),
            "p95_ms": round(s_lats[max(0, int(0.95 * len(s_lats)) - 1)], 2),
            "max_ms": round(s_lats[-1], 2),
        }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"summary": report["summary"], "latencies_ms": report["latencies_ms"], "report": str(REPORT_PATH)}))
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
