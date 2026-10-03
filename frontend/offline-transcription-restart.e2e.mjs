import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { writeFileSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from 'playwright-core';
const project=new URL('../',import.meta.url).pathname;
const root=join(project,'.var/phase8/browser-fixture');
const base='http://127.0.0.1:5589/';
let server;
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function start(){
 server=spawn(join(project,'.venv/bin/python'),['tests/e2e/offline_transcription_fixture_server.py',root,'--port','5588'],{cwd:project,stdio:'ignore'});
 for(let i=0;i<100;i++){try{const r=await fetch('http://127.0.0.1:5588/api/v1/local/transcription/capability');const d=await r.json();if(!d.capability.checking)return;}catch{}await pause(100);}
 throw new Error('isolated fixture server did not start');
}
async function stop(){if(server){const child=server;server=null;await new Promise(resolve=>{child.once('exit',resolve);child.kill('SIGTERM');});}}
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const external=[],errors=[];
try{
 writeFileSync(join(root,'executor','capability-mode.txt'),'READY');writeFileSync(join(root,'executor','result-mode.txt'),'slow');await start();
 const page=await browser.newPage({viewport:{width:768,height:1000}});
 page.on('request',r=>{if(!r.url().startsWith(base))external.push(r.url());});page.on('pageerror',e=>errors.push(String(e)));page.on('console',m=>{if(['error','warning'].includes(m.type()))errors.push(m.text());});
 await page.addInitScript(()=>localStorage.setItem('yia.ui-language','en'));
 const previous=JSON.parse(readFileSync(join(root,'browser-report.json'))).scenarios[0].mediaId;
 await page.goto(base+'#Content/'+previous);await page.locator('.timed-transcript').waitFor();
 // Import an actual short video through the user-facing picker.
 await page.getByRole('navigation').getByRole('button',{name:'Following',exact:true}).click();await page.getByRole('button',{name:'Add Source',exact:true}).first().click();await page.getByRole('button',{name:'Local files',exact:true}).click();
 const nonce=Buffer.from(String(Date.now()));const free=Buffer.alloc(8);free.writeUInt32BE(8+nonce.length);free.write('free',4);
 const video=Buffer.concat([readFileSync(join(root,'restart-video.mp4')),free,nonce]);
 const dialog=page.getByRole('dialog');await dialog.getByLabel('Choose local files').setInputFiles({name:'offline-restart-'+Date.now()+'.mp4',mimeType:'video/mp4',buffer:video});
 await dialog.getByRole('button',{name:'Confirm import',exact:true}).click();await dialog.getByRole('link',{name:'Open Content',exact:true}).click();
 const panel=page.getByRole('region',{name:'Offline transcription'});await panel.getByRole('button',{name:'Start transcription',exact:true}).click();
 await panel.getByRole('status').filter({hasText:'Transcribing…'}).waitFor();const id=page.url().split('#Content/')[1];
 await stop();await pause(400);await start();
 await page.reload();await page.getByRole('button',{name:'Retry transcription',exact:true}).waitFor();
 const status=await (await page.request.get(base+'api/v1/videos/'+id+'/transcription')).json();assert.equal(status.transcription.status,'INTERRUPTED');
 writeFileSync(join(root,'executor','result-mode.txt'),'success');await page.getByRole('button',{name:'Retry transcription',exact:true}).click();await page.locator('.timed-transcript li').waitFor();await page.locator('[id^="content-evidence-"]').first().waitFor();
 // A machine without a model keeps archived transcript/Summary/Evidence authority.
 writeFileSync(join(root,'executor','capability-mode.txt'),'MODEL_MISSING');await stop();await start();await page.reload();await page.locator('.timed-transcript').waitFor();await page.locator('[id^="content-evidence-"]').first().waitFor();
 await page.getByRole('region',{name:'Offline transcription'}).getByRole('status').filter({hasText:'Transcription complete'}).waitFor();
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:join(root,'screenshots','restart-video-model-absent.png'),fullPage:true});
 assert.deepEqual(external,[]);assert.deepEqual(errors,[]);
 writeFileSync(join(root,'restart-report.json'),JSON.stringify({videoId:id,previousAudioSurvived:true,crashDuringRunning:'INTERRUPTED',retry:'READY',modelAbsentExistingAuthority:'READY',external,errors},null,2));console.log('Video import/preprocess/crash/restart/retry/READY/absent-model authority passed.');
}finally{await stop();await browser.close();}
