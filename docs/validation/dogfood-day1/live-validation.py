"""Real public-provider checks against isolated runtime; never owner authority."""
import hashlib
import json
import sqlite3
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).with_name("live-validation.json")
BASE = "http://127.0.0.1:18965/api/v1"
results = {}
def request(method, path, data=None):
    body = None if data is None else json.dumps(data).encode()
    try:
        with urlopen(Request(BASE + path, data=body, method=method, headers={"Content-Type":"application/json", "X-YIA-Request":"local-ui", "Origin":"http://127.0.0.1:18965"}), timeout=180) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)
def save():
    compact = json.loads(json.dumps(results))
    # Preserve authority/counts/hashes without publishing public-video captions.
    for key in ("youtube_completed_detail",):
        if key not in compact or compact[key][0] != 200:
            continue
        detail = compact[key][1]
        transcript = detail.get("transcript", {})
        text = transcript.get("text", "")
        detail["transcript"] = {"status": transcript.get("status"), "characters": len(text), "sha256": hashlib.sha256(text.encode()).hexdigest(), "timed_segment_count": len(transcript.get("timed_segments", []))}
        note = detail.get("note", {}).get("v2", {})
        summary = note.get("summary", "") or ""
        detail["note"] = {"v2": {"status": note.get("status"), "summary_characters": len(summary), "summary_sha256": hashlib.sha256(summary.encode()).hexdigest(), "evidence_reference_count": len(note.get("evidence_references", [])), "key_point_count": len(note.get("key_points", []))}}
    OUTPUT.write_text(json.dumps(compact, ensure_ascii=False, indent=2)+"\n")

results["settings"] = request("GET", "/settings")
results["youtube_video"] = request("POST", "/sources/import", {"url":"https://youtu.be/aircAruvnKk", "command_id":"day1-real-video"})
results["content_immediate"] = request("GET", "/videos")
save()
assert any(item["video_id"] == "aircAruvnKk" for item in results["content_immediate"][1]["videos"])
save()
results["youtube_channel_handle"] = request("POST", "/sources/channels", {"input":"https://www.youtube.com/@3blue1brown/videos", "processing_mode":"ORGANIZE_CONTENT"})
save()
if results["youtube_channel_handle"][0] != 200:
    results["youtube_channel_id"] = request("POST", "/sources/channels", {"input":"https://www.youtube.com/channel/UCYO_jab_esuFRV4b17AJtAw", "processing_mode":"ORGANIZE_CONTENT"})
    save()
channel = results.get("youtube_channel_id", results["youtube_channel_handle"])
if channel[0] == 200:
    source = channel[1]["source"]
    results["pause"] = request("PATCH", "/sources/"+source["source_id"], {"enabled":False})
    results["resume"] = request("PATCH", "/sources/"+source["source_id"], {"enabled":True})
    with sqlite3.connect(ROOT / ".var/dogfood-day1/live-final/state.sqlite3") as db:
        db.row_factory=sqlite3.Row
        results["tracking_authority"] = dict(db.execute("SELECT * FROM source_tracking_state WHERE source_id=?", (source["source_id"],)).fetchone())
        results["baseline_observations"] = [dict(row) for row in db.execute("SELECT * FROM source_observations WHERE source_id=?", (source["source_id"],))]
        results["channel_content_count"] = db.execute("SELECT COUNT(*) FROM source_video_links WHERE source_id=?", (source["source_id"],)).fetchone()[0]
        assert results["channel_content_count"] == 0, "No historical baseline imports"
    save()
results["bilibili_video"] = request("POST", "/bilibili/imports", {"input":"https://www.bilibili.com/video/BV1GJ411x7h7/"})
results["sources_final"] = request("GET", "/sources")
results["content_final"] = request("GET", "/videos")
results["manual_intelligence"] = request("POST", "/videos/aircAruvnKk/intelligence", {"command_id":"day1-final-manual"})
results["youtube_completed_detail"] = request("GET", "/videos/aircAruvnKk")
results["intelligence_final"] = request("GET", "/intelligence")
results["topics_final"] = request("GET", "/topics")
if results["manual_intelligence"][0] == 202:
    from youtube_intel.state import SQLiteStateRepository
    execution = SQLiteStateRepository(ROOT / ".var/dogfood-day1/live-final/state.sqlite3").get_distillation_execution(results["manual_intelligence"][1]["execution"]["execution_id"])
    results["manual_invocation_count"] = execution.invocation_count
    assert execution.status == "WAITING_MODEL" and execution.invocation_count == 0
    assert results["youtube_completed_detail"][1]["note"]["v2"]["status"] == "AVAILABLE"
else:
    save()
    raise AssertionError("Real completed Content manual analysis must persist readiness")
save()
print("Isolated public-provider evidence recorded:", {key:value[0] for key,value in results.items() if isinstance(value, tuple)})
