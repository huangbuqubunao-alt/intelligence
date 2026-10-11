import {chromium} from '../../../../frontend/node_modules/playwright-core/index.mjs';
import {execFileSync} from 'node:child_process';
import {writeFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const root='docs/validation/muse-final-audit',base='http://127.0.0.1:5688/';
const ctx=await chromium.launchPersistentContext('.var/muse-final-audit/gui/browser-profile',{executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,viewport:{width:1440,height:1000}});
const p=ctx.pages()[0],posts=[],errors=[];p.on('pageerror',e=>errors.push(String(e)));p.on('request',r=>{if(r.method()==='POST')posts.push({url:r.url().replace(/\/picks\/[^/]+/,'/picks/<grant>'),bytes:Buffer.byteLength(r.postData()??''),body:r.postData()})});
try{
await p.goto(base+'#Following');await p.getByRole('heading',{name:'关注',exact:true}).waitFor();await p.getByRole('button',{name:'添加关注',exact:true}).first().click();await p.getByRole('button',{name:'导入本地文件',exact:true}).click();await p.getByRole('button',{name:'选择本地文件',exact:true}).click();
await p.waitForTimeout(600);
execFileSync('/usr/sbin/screencapture',['-x','-R315,136,881,448',root+'/screenshots/07-real-appkit-picker.png']);
execFileSync('/usr/bin/osascript',['-e',`tell application "System Events"
 tell process "IntelligenceFilePicker"
  set frontmost to true
  keystroke "g" using {command down, shift down}
  delay 1
  keystroke "a" using {command down}
  keystroke "/Users/hua/Documents/yia-worktrees/muse-final-audit/.var/muse-final-audit/gui/fixtures/audit-media.mp4"
  key code 36
  delay 2
  click button "Open" of splitter group 1 of window 1
 end tell
end tell`]);
await p.getByRole('button',{name:'确认导入',exact:true}).waitFor({timeout:45000});await p.screenshot({path:root+'/screenshots/08-media-selected.png'});await p.getByRole('button',{name:'确认导入',exact:true}).click();
await p.waitForURL(/#Content\//,{timeout:60000});await p.getByRole('heading',{name:'audit-media.mp4',exact:true}).waitFor();await p.waitForTimeout(500);await p.screenshot({path:root+'/screenshots/09-media-content.png'});
const response=await ctx.request.post(base+'api/v1/local/native/jobs',{data:{},headers:{'Origin':base.slice(0,-1),'X-YIA-Request':'local-ui'}});const jobs=(await response.json()).jobs;
const f=jobs.flatMap(j=>j.files).find(f=>f.filename==='audit-media.mp4');assert.equal(f.snapshot_method,'APFS_CLONE');assert.ok(posts.every(r=>!r.url.includes('/local/imports')));assert.ok(posts.filter(r=>r.url.includes('/local/native/')).every(r=>r.bytes===2&&r.body==='{}'));
writeFileSync(root+'/gui-media.json',JSON.stringify({realMacOS:true,realAppKit:true,realMediaFixture:true,mediaBytes:f.byte_count,snapshotMethod:f.snapshot_method,httpFileBytes:0,posts,errors,job:f},null,2)+'\n');console.log('REAL_APPKIT_APFS_SMALL_MEDIA_PASS',f);
}finally{await ctx.close()}
