"""Fresh-process verification of acoustic authority and portable restore."""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from scripts.verify_phase9_product import database, trusted, wait
from youtube_intel.acoustic_qualification import (
    canonical,
    current_tuple,
    qualification_status,
)
from youtube_intel.backup_restore import BackupRestoreService
from youtube_intel.local_transcription_jobs import LocalTranscriptionJobs
from youtube_intel.offline_transcription import model_identity
from youtube_intel.state import SQLiteStateRepository


def no_authority(repo, samples):
    for sample in samples:
        assert repo.get_verified_timed_transcript(video_id=sample['content_id']) is None
        assert repo.current_local_summary_pointer(sample['content_id']) is None
        assert not repo.list_evidence_for_presentation(sample['content_id'])
    return [sample['content_id'] for sample in samples]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    report = json.loads((root/'report.json').read_bytes())
    assert report['verdict'] == 'PASSED' and len(report['samples']) == 17
    samples = [s for s in report['samples'] if s['trusted_timed_transcript']]
    controls = [s for s in report['samples'] if s.get('no_authority')]
    assert len(samples) == 14 and len(controls) == 3
    repo = SQLiteStateRepository(root/'state.sqlite3')
    repo.bind_source_storage(root/'data')
    jobs = LocalTranscriptionJobs(repo, root/'data')  # ordinary product factory
    wait(lambda: not jobs.capability()['checking'])
    capability = jobs.capability()
    assert capability['state'] == 'READY'
    assert capability['qualification_state'] == 'PASSED' and capability['production_eligible']
    model = jobs.executor.model_path
    assert model is not None
    identity = current_tuple(model, model_identity(model), json.loads((model/'model-origin.json').read_bytes()))
    assert identity == report['qualification_tuple']
    assert qualification_status(root/'.local-transcription', identity)['state'] == 'PASSED'
    assert qualification_status(root/'.local-transcription', None) == {'state':'STALE','production_eligible':False}
    output = {'fresh_process_capability':capability, 'fresh_tuple_identical':True,
              'changed_or_absent_tuple_fail_closed':True,
              'restart_authority':[trusted(repo,s) for s in samples],
              'restart_refused_controls':no_authority(repo,controls)}
    jobs.configure(None)  # isolated config only, preserves receipt and source authority
    wait(lambda: not jobs.capability()['checking'])
    assert jobs.capability()['state'] == 'MODEL_MISSING' and not jobs.capability()['production_eligible']
    output['model_absence_authority'] = [trusted(repo,s) for s in samples]
    output['model_absence_controls'] = no_authority(repo,controls)
    jobs.configure(str(model))
    wait(lambda: not jobs.capability()['checking'])
    assert jobs.capability()['qualification_state'] == 'PASSED' and jobs.capability()['production_eligible']
    backups = BackupRestoreService(database=root/'state.sqlite3', data_root=root/'data')
    created = backups.create_backup()
    archive_path, _ = backups.backup_download(created.backup_id)
    with zipfile.ZipFile(archive_path) as archive:
        assert not any('weights' in n or '.local-transcription' in n or 'qualification.seal' in n for n in archive.namelist())
    target = root/'restored-product'
    target.mkdir(exist_ok=False)
    restore = BackupRestoreService(database=target/'state.sqlite3', data_root=target/'data')
    staged = restore.stage_restore(archive_path.read_bytes())
    restore.confirm_restore(staged.restore_id)
    restore.recover_and_apply_pending_restore()
    restored = SQLiteStateRepository(target/'state.sqlite3')
    restored.bind_source_storage(target/'data')
    absent = LocalTranscriptionJobs(restored, target/'data')
    wait(lambda: not absent.capability()['checking'])
    assert absent.capability()['state'] == 'MODEL_MISSING'
    assert absent.capability()['qualification_state'] == 'NOT_TESTED' and not absent.capability()['production_eligible']
    output['backup_restore'] = {'backup_id':created.backup_id,'model_and_receipt_excluded':True,
        'authority':[trusted(restored,s) for s in samples],
        'refused_controls':no_authority(restored,controls),'qualification_not_inherited':True}
    output['databases'] = {'real':database(repo),'restored':database(restored)}
    (root/'product-verification.json').write_bytes(canonical(output))
    print(json.dumps({'restart_authority':len(samples),'controls':len(controls),
        'ordinary_factory_qualified':True,'backup_restore':'PASSED','owner_data_access':False}))


if __name__ == '__main__':
    main()
