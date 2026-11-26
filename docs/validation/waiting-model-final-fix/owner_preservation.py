"""Release preservation only: snapshots owner data without testing or resetting it.

Run only after adoption gates pass and the owned services have stopped.
All raw owner data stays in an ignored, private task directory.
"""
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

PROJECT = Path('/Users/developer/Documents/yia-worktrees/v1x-local-main')
OWNER = PROJECT / '.var/owner'
SAFE = Path(__file__).resolve().parents[3] / '.var/waiting-model-final-fix/owner-preservation'


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def fingerprints():
    with sqlite3.connect((OWNER / 'state.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        rows = {}
        for name in tables:
            values = sorted([list(r) for r in db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')], key=json.dumps)
            rows[name] = {'count': len(values), 'sha256': hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()}
        history = [list(r) for r in db.execute('SELECT * FROM schema_migrations ORDER BY version')]
        version = db.execute('PRAGMA user_version').fetchone()[0]
    data = {str(p.relative_to(OWNER / 'data')): digest(p) for p in sorted((OWNER / 'data').rglob('*')) if p.is_file()}
    config = {str(p.relative_to(OWNER / 'config')): digest(p) for p in sorted((OWNER / 'config').rglob('*')) if p.is_file()}
    return {'schema': version, 'tables': rows, 'history': history, 'data': data, 'config': config}


if __name__ == '__main__':
    assert sys.argv[1] in {'snapshot', 'verify-migration'}
    if sys.argv[1] == 'snapshot':
        SAFE.mkdir(parents=True, exist_ok=False)
        SAFE.chmod(0o700)
        before = fingerprints()
        assert before['schema'] == 36
        with sqlite3.connect((OWNER / 'state.sqlite3').as_uri() + '?mode=ro', uri=True) as source:
            with sqlite3.connect(SAFE / 'state-schema36.sqlite3') as target:
                source.backup(target)
                assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        subprocess.run(['/bin/cp', '-cR', str(OWNER / 'data'), str(SAFE / 'data')], check=True)
        clone = {str(p.relative_to(SAFE / 'data')): digest(p) for p in sorted((SAFE / 'data').rglob('*')) if p.is_file()}
        assert clone == before['data']
        (SAFE / 'before.json').write_text(json.dumps(before, sort_keys=True, indent=2))
        print('Owner preservation snapshot verified; raw data is private and ignored.')
    else:
        before = json.loads((SAFE / 'before.json').read_text())
        after = fingerprints()
        assert after['schema'] == 37
        assert after['data'] == before['data'] and after['config'] == before['config']
        for name, values in before['tables'].items():
            if name != 'schema_migrations':
                assert after['tables'][name] == values, name
        assert set(after['tables']) == set(before['tables']) | {'distillation_waiting_model_cancellations'}
        assert after['tables']['distillation_waiting_model_cancellations']['count'] == 0
        assert after['history'][:-1] == before['history']
        assert after['history'][-1][0:2] == [37, '037_add_waiting_model_cancellation.sql']
        (SAFE / 'after-migration.json').write_text(json.dumps(after, sort_keys=True, indent=2))
        print('Owner migration verified: every pre-existing row and DATA/config hash preserved.')
