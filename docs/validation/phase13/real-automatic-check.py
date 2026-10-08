import http.client,json,sqlite3,time
from datetime import UTC,datetime,timedelta
from pathlib import Path
root=Path('/tmp/intelligence-phase13-evidence/dogfood-runtime');source='youtube-channel-UCLA_DiR1FfKNvjuUpBHmylQ'
assert not (root/'simulate-offline').exists()
def api(method,path,data=None):
 c=http.client.HTTPConnection('127.0.0.1',18865,timeout=70);c.request(method,path,json.dumps(data or {}) if method!='GET' else None,{'X-YIA-Request':'local-ui','Content-Type':'application/json'});r=c.getresponse();body=json.loads(r.read());c.close();assert r.status<400,(r.status,body);return body
before=api('GET','/api/v1/sources/'+source)['source']
with sqlite3.connect(root/'state.sqlite') as db:
 previous_runs={row[0] for row in db.execute('SELECT run_id FROM source_runs')}
 db.execute('UPDATE source_tracking_state SET next_check_at=? WHERE source_id=?',((datetime.now(UTC)-timedelta(seconds=1)).isoformat(),source))
start=time.monotonic();api('PATCH','/api/v1/sources/'+source,{'enabled':True})
until=time.monotonic()+65
while time.monotonic()<until:
 with sqlite3.connect(root/'state.sqlite') as db:
  rows=[dict(zip(['run_id','state','command'],r)) for r in db.execute('SELECT run_id,state,manual_command_id FROM source_runs') if r[0] not in previous_runs]
 if rows and all(r['state'] in {'COMPLETED','FAILED'} for r in rows):break
 time.sleep(.1)
else:raise AssertionError('real automatic check did not settle within accepted feed bound')
after=api('GET','/api/v1/sources/'+source)['source'];assert len(rows)==1 and rows[0]['command'].startswith('following-auto:')
assert after['tracking']['checking'] is False
with sqlite3.connect(root/'state.sqlite') as db:
 counts={table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ['videos','source_observations','source_checks','source_runs','distillation_execution_checkpoints']}
 assert counts['videos']==0 and counts['distillation_execution_checkpoints']==0
if rows[0]['state']=='FAILED':
 assert after['tracking']['verified_at']==before['tracking']['verified_at']
 assert after['tracking']['health']=='NOT_FOUND'
 assert datetime.fromisoformat(after['tracking']['next_check_at'].replace('Z','+00:00'))-datetime.now(UTC)>timedelta(minutes=59)
result={'normal_mac_vpn_proxy':True,'system_settings_changed':False,'feed_or_route_fixture':False,'only_due_time_test_seam':True,'seconds':round(time.monotonic()-start,3),'before':before,'after':after,'runs':rows,'counts':counts}
Path('/tmp/intelligence-phase13-evidence/real-automatic-check.json').write_text(json.dumps(result,indent=2));print(rows[0]['state'],after['tracking']['health'],'one real automatic run, zero historical Content/model work')
