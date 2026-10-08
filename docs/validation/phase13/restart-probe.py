import http.client,json,sqlite3,sys
from pathlib import Path
root=Path('/tmp/intelligence-phase13-evidence/dogfood-runtime');kind=sys.argv[1]
c=http.client.HTTPConnection('127.0.0.1',18865,timeout=10);c.request('GET','/api/v1/sources');r=c.getresponse();sources=json.loads(r.read())['sources'];assert r.status==200;c.close()
with sqlite3.connect(root/'state.sqlite') as db:
 integrity=db.execute('PRAGMA integrity_check').fetchall();foreign=db.execute('PRAGMA foreign_key_check').fetchall()
 counts={table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ['source_checks','source_runs','source_observations','videos','distillation_execution_checkpoints']}
 running=db.execute("SELECT COUNT(*) FROM source_checks WHERE status='RUNNING'").fetchone()[0]
 schema=db.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
assert integrity==[('ok',)] and foreign==[] and running==0 and schema==34
state={'sources':sources,'counts':counts,'generation':int((root/'generation.txt').read_text()),'schema':schema,'integrity':integrity,'foreign_keys':foreign,'running_checks':running}
path=Path('/tmp/intelligence-phase13-evidence/restart-'+kind+'.json');path.write_text(json.dumps(state,indent=2))
if kind=='after':
 before=json.loads(Path('/tmp/intelligence-phase13-evidence/restart-before.json').read_text())
 assert state['sources']==before['sources'] and counts==before['counts']
 assert state['generation']>before['generation']
 assert any(not s['enabled'] for s in sources)
print(kind,'restart authority/schema/integrity PASS',counts)
