import http.client,json,time
from pathlib import Path
root=Path('/tmp/intelligence-phase13-evidence/dogfood-runtime')
source='youtube-channel-UCLA_DiR1FfKNvjuUpBHmylQ'
def api(method,path,data=None,raw=None):
 c=http.client.HTTPConnection('127.0.0.1',18865,timeout=15)
 c.request(method,path,raw if raw is not None else json.dumps(data or {}) if method!='GET' else None,{'X-YIA-Request':'local-ui','Content-Type':'application/zip' if raw is not None else 'application/json'})
 r=c.getresponse();b=r.read();c.close();result=json.loads(b) if r.getheader('Content-Type','').startswith('application/json') else b
 assert r.status<400,(path,r.status,result)
 return result
before_generation=int((root/'generation.txt').read_text())
api('PATCH','/api/v1/sources/'+source,{'enabled':False})
saved=api('GET','/api/v1/sources/'+source)['source']
assert api('GET','/api/v1/backup-restore/status')['status']['ready']
backup=api('POST','/api/v1/backup-restore/backups')['backup']
archive=api('GET','/api/v1/backup-restore/backups/'+backup['backup_id']+'/download')
assert isinstance(archive,bytes)
# Pre-restore in-memory/runtime world differs from archived authority.
api('PATCH','/api/v1/sources/'+source,{'enabled':True})
preview=api('POST','/api/v1/backup-restore/restore/stage',raw=archive)['restore']
confirmed=api('POST','/api/v1/backup-restore/restore/confirm',{'restore_id':preview['restore_id']})['restore']
assert confirmed['restart_required']
until=time.monotonic()+20
while time.monotonic()<until:
 try:
  restored=api('GET','/api/v1/sources/'+source)['source']
  generation=int((root/'generation.txt').read_text())
  if generation>before_generation and restored['enabled'] is False:break
 except (ConnectionError,OSError):pass
 time.sleep(.1)
else:raise AssertionError('runtime restore did not rebuild')
assert restored['tracking']==saved['tracking']
assert restored['last_success_at']==saved['last_success_at']
readiness=api('GET','/api/v1/backup-restore/status')
assert readiness['status']['ready']
Path('/tmp/intelligence-phase13-evidence/restore-runtime.json').write_text(json.dumps({'saved':saved,'restored':restored,'before_generation':before_generation,'after_generation':generation,'confirmed':confirmed,'readiness':readiness,'archive_size':len(archive)},indent=2))
print('actual API Backup/Restore rebuilt the runtime; paused source and complete scheduling authority restored exactly')
