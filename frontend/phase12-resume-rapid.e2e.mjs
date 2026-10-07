import assert from 'node:assert/strict';
import { writeFileSync } from 'node:fs';
import { chromium } from 'playwright-core';
const base='http://127.0.0.1:5713/';
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
try {
 const page=await browser.newPage();
 const get=async path=>{const r=await page.request.get(base+'api/v1/'+path);assert.equal(r.status(),200);return r.json();};
 const post=async(path,data={})=>{const r=await page.request.post(base+'api/v1/'+path,{headers:{Origin:base.slice(0,-1),'X-YIA-Request':'local-ui'},data});assert.ok(r.ok(),await r.text());return r.json();};
 await post('fixture/advance',{index:0,publish:false});
 const results=[];
 for(const id of ['youtube-channel-UC0000000000000000000000','bilibili-creator-123']) {
  const before=await get('sources/'+id), runIds=new Set(before.source_runs.map(r=>r.run_id));
  const responses=await Promise.all(Array.from({length:12},()=>post('sources/'+id+'/check',{command_id:crypto.randomUUID()})));
  let after;
  for(let i=0;i<60;i++){after=await get('sources/'+id);if(!after.source.tracking.checking)break;await page.waitForTimeout(500);}
  assert.equal(after.source.tracking.checking,false);
  assert.equal(after.source.tracking.verified_at,before.source.tracking.verified_at);
  assert.equal(after.source.last_success_at,before.source.last_success_at);
  assert.equal(after.source.tracking.update_count,before.source.tracking.update_count);
  const newRuns=after.source_runs.filter(r=>!runIds.has(r.run_id));
  if(id.startsWith('youtube')){assert.equal(newRuns.length,1);assert.equal(newRuns[0].state,'FAILED');assert.equal(after.source.tracking.health,'OFFLINE');}
  else{assert.equal(newRuns.length,0);assert.ok(responses.every(r=>r.status==='CAPABILITY_UNAVAILABLE'));}
  results.push({source:id,commands:12,new_runs:newRuns.length,frontier_preserved:true,last_success_preserved:true,updates_preserved:true,health:after.source.tracking.health});
 }
 const readiness=(await get('backup-restore/status')).status;assert.equal(readiness.ready,true);
 writeFileSync(new URL('../docs/validation/phase12-resume/rapid-check.json',import.meta.url),JSON.stringify({kind:'FIXTURE/REPLAY',results,backup_readiness:readiness},null,2)+'\n');
 console.log('Concurrent Check Now bounds and offline Backup readiness passed');
} finally {await browser.close();}
