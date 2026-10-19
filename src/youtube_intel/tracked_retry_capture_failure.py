"""Closed, non-authoritative capture failures eligible for a new manual command."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from youtube_intel.source_authority import read_managed, sha256
from youtube_intel.state import (
    SQLiteStateRepository,
    _parse_utc_datetime,
    format_utc_datetime,
)
from youtube_intel.tracked_retry_context import RetryIntegrity
from youtube_intel.tracked_retry_files import provenance, read_buffer
from youtube_intel.tracked_retry_store import canonical, digest
from youtube_intel.transcripts import (
    SUBTITLE_QUALITY_POLICY,
    TranscriptError,
    TranscriptJobContext,
    _capture_artifact_write,
    _decode_source_metadata,
    normalize_language_tag,
    normalize_timed_subtitle,
)


def _time(value: Any) -> str:
    if type(value) is not str or format_utc_datetime(_parse_utc_datetime(value)) != value:
        raise RetryIntegrity('Content retry capture failure time changed')
    return value


def _verify_capture_failure(
    connection: sqlite3.Connection, request: dict[str, Any], execution: dict[str, Any],
    target: sqlite3.Row, call: sqlite3.Row, dispatch: sqlite3.Row, *, data_root: Path | None,
) -> None:
    """Never grants authority to captures or repairs the original terminal row.

    Called for every ancestor from the iterative store reader. The explicit
    trusted DATA root is mandatory; a database-only assertion is insufficient.
    """
    if data_root is None or not data_root.is_absolute():
        raise RetryIntegrity('Content retry capture parent requires its bound DATA root')
    history = json.loads(execution['events_json'])
    terminal = history[-1]
    marker = history[-2] if len(history) >= 2 else {}
    attempts = connection.execute('SELECT * FROM job_attempts WHERE job_id=?', (target['job_id'],)).fetchall()
    end = _time(execution['finished_at'])
    if (execution['state'] != 'FAILED' or execution['error_code'] != 'LOCAL_FINALIZATION_FAILED'
        or execution['local_attempt_count'] != 0 or execution['revision'] != terminal['revision']
        or any(execution[k] is not None for k in ('lease_owner','lease_until','canonical_artifact_id','timed_transcript_id','summary_artifact_id','completion_json','completion_sha256'))
        or target['status'] != 'FAILED_FINAL' or target['attempt_count'] != 1
        or target['last_error_code'] != 'INVALID_RESPONSE' or target['last_error_message'] != execution['error_code']
        or any(target[k] is not None for k in ('lease_owner','lease_until'))
        or call['status'] != 'FAILED_FINAL' or call['attempt_count'] != 1
        or call['last_error_code'] != 'LOCAL_RESOURCE' or call['last_error_message'] != execution['error_code']
        or any(call[k] is not None for k in ('reservation_owner','lease_until','response_artifact_id','input_tokens','output_tokens','cost_microusd'))
        or dispatch['status'] != 'FAILED_KNOWN'
        or any(_time(value) != end for value in (execution['updated_at'],target['updated_at'],target['finished_at'],call['updated_at'],call['finished_at'],dispatch['updated_at'],terminal['at']))
        or terminal['event'] != 'FAILED' or terminal['prior_state'] != 'ACQUIRING' or terminal['action'] is not None
        or marker.get('event') != 'DISPATCH_INTENT' or marker.get('state') != 'ACQUIRING'
        or marker['fencing_epoch'] != execution['fencing_epoch'] or terminal['fencing_epoch'] != marker['fencing_epoch']
        or len(attempts) != 1):
        raise RetryIntegrity('Content retry known capture failure receipt changed')
    attempt = attempts[0]
    first_claim = next((item for item in history if item['event'] == 'CLAIMED'), None)
    if (first_claim is None or attempt['attempt_number'] != 1 or attempt['outcome'] != 'FAILED_FINAL'
        or attempt['error_code'] != target['last_error_code'] or attempt['error_message'] != execution['error_code']
        or _time(attempt['finished_at']) != end or _time(attempt['started_at']) != first_claim['at']
        or re.fullmatch(r'tracked-retry-[0-9a-f]{32}', attempt['lease_owner'] or '') is None
        or not _time(attempt['started_at']) <= _time(call['available_at']) <= _time(call['started_at']) <= marker['at'] <= end < _time(attempt['lease_until'])):
        raise RetryIntegrity('Content retry capture failure real attempt changed')
    files = [dict(row) for row in connection.execute('SELECT * FROM tracked_content_retry_files WHERE request_id=?', (request['request_id'],))]
    captures = [row for row in files if row['role'] == 'CAPTURE']
    if not 1 <= len(captures) <= 2 or len(files) != 2 * len(captures):
        raise RetryIntegrity('Content retry capture failure file set changed')
    by_path = {row['relative_path']: row for row in files}
    if len(by_path) != len(files):
        raise RetryIntegrity('Content retry capture failure file identity is ambiguous')
    parameters = json.loads(request['parameters_json'])
    repository = SQLiteStateRepository(connection.execute('PRAGMA database_list').fetchone()[2])
    expected_artifacts: dict[str, Any] = {}
    formats = []
    expected_paths: set[str] = set()
    for row in captures:
        proof = json.loads(row['proof_json'])
        if not isinstance(proof, dict):
            raise RetryIntegrity('Content retry capture failure proof is not an object')
        epoch = proof.get('fencing_epoch')
        if (type(epoch) is not int or epoch != execution['fencing_epoch'] or row['state'] != 'VERIFIED'
            or row['expected_sha256'] != row['observed_sha256'] or row['expected_size_bytes'] != row['observed_size_bytes']
            or not marker['at'] <= _time(row['created_at']) <= _time(row['settled_at']) <= end):
            raise RetryIntegrity('Content retry capture failure capture is not fully verified')
        try:
            body = read_managed(data_root, row['relative_path'], maximum=SUBTITLE_QUALITY_POLICY.max_raw_bytes)
            role, rebuilt = provenance(repository, data_root, request, row['relative_path'], body, epoch=epoch)
        except OSError as error:
            raise RetryIntegrity('Content retry capture failure bytes are missing or unsafe') from error
        if (role != 'CAPTURE' or proof != rebuilt or canonical(proof) != row['proof_json'] or digest(proof) != row['proof_sha256']
            or sha256(body) != row['expected_sha256'] or len(body) != row['expected_size_bytes']):
            raise RetryIntegrity('Content retry capture failure producer or bytes changed')
        buffer = str(Path(row['relative_path']).with_name('.tracked-buffer-' + digest(dict(request_id=request['request_id'],relative=row['relative_path'],epoch=epoch))))
        expected_paths.update((row['relative_path'], buffer))
        buffered = by_path.get(buffer)
        if (buffered is None or buffered['role'] != 'WRITE_BUFFER' or buffered['state'] != 'ABSENT'
            or any(buffered[k] is not None for k in ('observed_sha256','observed_size_bytes'))
            or any(buffered[k] != row[k] for k in ('expected_sha256','expected_size_bytes','proof_json','proof_sha256'))
            or not row['created_at'] <= _time(buffered['created_at']) <= _time(buffered['settled_at']) <= end):
            raise RetryIntegrity('Content retry capture failure buffer is not settled absent')
        try:
            read_buffer(data_root, buffer)
        except FileNotFoundError:
            pass
        except OSError as error:
            raise RetryIntegrity('Content retry capture failure buffer is unsafe') from error
        else:
            raise RetryIntegrity('Content retry capture failure absent buffer exists')
        metadata = _decode_source_metadata(Path(row['relative_path']).name, video_id=request['video_id'])
        normalized = normalize_timed_subtitle(body, metadata.source_format)
        formats.append((metadata, normalized, row['created_at']))
        artifact = _capture_artifact_write(video_id=request['video_id'], context=TranscriptJobContext(job_id=request['target_job_id'],owner='proof',pipeline_version=request['pipeline_version'],refresh_generation=request['refresh_generation']),raw_request_hash=request['raw_request_hash'],metadata=metadata,content_hash=normalized.source_content_hash,provider=parameters['adapter_name'],provider_version=parameters['adapter_version'])
        expected_artifacts[artifact.artifact_id] = (artifact, row['created_at'])
    if set(by_path) != expected_paths:
        raise RetryIntegrity('Content retry capture failure contains extra files')
    if len(formats) == 2:
        plain = [item for item in formats if not item[1].timed_cues]
        timed = [item for item in formats if item[1].timed_cues]
        if len(plain) != 1 or len(timed) != 1:
            raise RetryIntegrity('Content retry capture failure alternate is not a native timing pair')
        first, second = plain[0], timed[0]
        if (first[0].source_type != second[0].source_type
            or normalize_language_tag(first[0].actual_language) != normalize_language_tag(second[0].actual_language)
            or first[0].requested_language != second[0].requested_language
            or first[0].source_format == second[0].source_format or second[0].source_format.value not in {'vtt','srt'}
            or first[2] > second[2]):
            raise RetryIntegrity('Content retry capture failure native alternate source changed')
    for row in connection.execute('SELECT * FROM artifacts WHERE job_id=?', (target['job_id'],)):
        expected = expected_artifacts.get(row['artifact_id'])
        if expected is None:
            raise RetryIntegrity('Content retry capture failure has authoritative artifacts')
        artifact, created = expected
        fields = dict(artifact_key=artifact.artifact_key,video_id=artifact.video_id,job_id=artifact.job_id,kind=artifact.kind.value,storage_root=artifact.storage_root.value,relative_path=artifact.relative_path,content_hash=artifact.content_hash,provider=artifact.provider,model=None,producer_version=artifact.producer_version,retention_class=artifact.retention_class.value,expires_at=None,deleted_at=None)
        if any(row[k] != value for k, value in fields.items()) or not created <= _time(row['created_at']) <= end:
            raise RetryIntegrity('Content retry capture failure indexed source changed')
    queries = (
        'SELECT 1 FROM timed_transcripts t JOIN artifacts a ON a.artifact_id=t.canonical_artifact_id WHERE a.job_id=?',
        'SELECT 1 FROM evidence e JOIN artifacts a ON a.artifact_id=e.artifact_id WHERE a.job_id=?',
        'SELECT 1 FROM evidence_text_bindings e JOIN timed_transcripts t USING(timed_transcript_id) JOIN artifacts a ON a.artifact_id=t.canonical_artifact_id WHERE a.job_id=?',
        'SELECT 1 FROM evidence_source_ranges e JOIN artifacts a ON a.artifact_id=e.canonical_artifact_id WHERE a.job_id=?',
        'SELECT 1 FROM current_content_summaries s JOIN artifacts a ON a.artifact_id=s.analysis_artifact_id WHERE a.job_id=?',
    )
    if any(connection.execute(query, (target['job_id'],)).fetchone() is not None for query in queries):
        raise RetryIntegrity('Content retry capture failure gained downstream authority')


def verify_capture_failure(
    connection: sqlite3.Connection, request: dict[str, Any], execution: dict[str, Any],
    target: sqlite3.Row, call: sqlite3.Row, dispatch: sqlite3.Row, *, data_root: Path | None,
) -> None:
    try:
        _verify_capture_failure(connection, request, execution, target, call, dispatch, data_root=data_root)
    except RetryIntegrity:
        raise
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, OSError, TranscriptError) as error:
        raise RetryIntegrity('Content retry capture failure typed proof is invalid') from error
