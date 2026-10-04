import assert from 'node:assert/strict';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from 'playwright-core';

const base='http://127.0.0.1:5599/';
const root=new URL('../.var/phase9/',import.meta.url).pathname;
const run=JSON.parse(readFileSync(join(root,'results-corrected-v1','qualification.json')));
const info=JSON.parse(readFileSync(join(root,'model-manifest.json')));
const model=join(root,'models','whisper-large-v3-turbo',info.revision);
const samples=Object.fromEntries(run.samples.map(s=>[s.id,s]));
const screenshot=join(root,'real-browser-screenshots');mkdirSync(screenshot,{recursive:true});
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const errors=[],external=[],scenarios=[];
const freshId=JSON.parse(readFileSync(join(root,'product-verification.json'))).backup_restore.new_transcription;
assert.equal(freshId,'MODEL_MISSING');
try {
for(const language of ['zh-CN','en']) for(const width of [320,768,1024,1440]) {
 const page=await browser.newPage({viewport:{width,height:1000}});
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('console',m=>{if(['error','warning'].includes(m.type()))errors.push(m.text());});
 page.on('request',r=>{if(!r.url().startsWith(base))external.push(r.url());});
 await page.route('**/*',route=>route.request().url().startsWith(base)?route.continue():route.abort());
 await page.addInitScript(lang=>localStorage.setItem('yia.ui-language',lang),language);
 const text=(en,zh)=>language==='en'?en:zh;
 const get=async path=>{const response=await page.request.get(base+'api/v1/'+path);assert.equal(response.status(),200);return response.json();};
 const noOverflow=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`${language}/${width} overflow`);
 const waitCapability=async()=>{for(let attempt=0;attempt<100;attempt++){const c=(await get('local/transcription/capability')).capability;if(!c.checking)return c;await page.waitForTimeout(200);}throw new Error('bounded capability timeout');};
 for(const name of ['mandarin-clean','english-clean','english-video']) {
  const sample=samples[name];
  await page.goto(base+'#Content/'+sample.content_id);
  await page.locator('.timed-transcript li').first().waitFor();
  await page.locator('[id^="content-evidence-"]').first().waitFor();
  const detail=await get('videos/'+sample.content_id);
  assert.deepEqual(detail.transcript.timed_segments.map(c=>({start_ms:c.start_ms,end_ms:c.end_ms,text:c.text})),sample.cues);
  assert.equal(detail.video.source_language,name==='mandarin-clean'?'zh':'en');
  const panel=page.getByRole('region',{name:text('Offline transcription','离线转写')});
  await panel.locator('summary').click();
  await panel.getByText(text('Acoustic qualification failed','资格验证失败'),{exact:true}).waitFor();
  assert.equal(await panel.getByRole('button',{name:text('Start transcription','开始转写'),exact:true}).count(),0);
  await noOverflow();await page.screenshot({path:join(screenshot,`${language}-${width}-${name}.png`),fullPage:true});
 }
 await page.getByRole('navigation').getByRole('button',{name:text('Settings','设置'),exact:true}).click();
 await page.getByLabel(text('Preferred output language','默认输出语言')).selectOption('en');
 assert.equal((await get('settings')).general.output_language,'en');
 await page.goto(base+'#Content/'+samples['mandarin-clean'].content_id);
 await page.locator('.timed-transcript li').first().waitFor();
 assert.equal((await get('videos/'+samples['mandarin-clean'].content_id)).video.source_language,'zh');
 assert.ok((await page.locator('.timed-transcript').innerText()).includes('公共图书馆'));
 assert.equal(await page.locator('.sidebar-nav button').count(),6);
 const all=(await get('videos')).videos;
 const fresh=all.find(v=>v.title==='fresh-short.wav');assert.ok(fresh);
 await page.goto(base+'#Content/'+fresh.video_id);
 let panel=page.getByRole('region',{name:text('Offline transcription','离线转写')});
 await panel.getByRole('status').filter({hasText:text('Acoustic qualification required','需要语音转写资格验证')}).waitFor();
 await panel.locator('summary').click();
 await panel.getByText(text('Acoustic qualification failed','资格验证失败'),{exact:true}).waitFor();
 await noOverflow();await page.screenshot({path:join(screenshot,`${language}-${width}-blocked.png`),fullPage:true});
 const changed=await page.request.put(base+'api/v1/local/transcription/model',{data:{model_path:null},headers:{'X-YIA-Request':'local-ui'}});assert.ok(changed.ok());
 assert.equal((await waitCapability()).state,'MODEL_MISSING');
 await page.reload();await panel.getByRole('status').filter({hasText:text('Local model is missing','缺少本地模型')}).waitFor();
 await panel.locator('summary').click();await noOverflow();await page.screenshot({path:join(screenshot,`${language}-${width}-missing.png`),fullPage:true});
 await page.goto(base+'#Content/'+samples['mandarin-clean'].content_id);
 await page.locator('.timed-transcript li').first().waitFor();await page.locator('[id^="content-evidence-"]').first().waitFor();
 assert.deepEqual((await get('videos/'+samples['mandarin-clean'].content_id)).transcript.timed_segments.map(c=>({start_ms:c.start_ms,end_ms:c.end_ms,text:c.text})),samples['mandarin-clean'].cues);
 panel=page.getByRole('region',{name:text('Offline transcription','离线转写')});
 await panel.locator('summary').click();
 await panel.getByLabel(text('Local MLX model directory','本地 MLX 模型目录')).fill(model);
 await Promise.all([
  page.waitForResponse(response=>response.url().endsWith('/local/transcription/model') && response.request().method()==='PUT'),
  panel.getByRole('button',{name:text('Use local model','使用本地模型'),exact:true}).click(),
 ]);
 assert.equal((await waitCapability()).qualification_state,'FAILED');
 await panel.getByText(text('Acoustic qualification failed','资格验证失败'),{exact:true}).waitFor();
 assert.ok(!(await page.locator('body').innerText()).includes('/Users/'));
 await noOverflow();await page.reload();await page.locator('[id^="content-evidence-"]').first().waitFor();
 scenarios.push({language,width,real_audio:true,real_video:true,qualification:'FAILED',new_transcription_blocked:true,model_missing_preserves_authority:true,source_language_preserved_with_english_output:true});
 await page.close();
}
assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
writeFileSync(join(root,'real-browser-report.json'),JSON.stringify({scenarios,errors,external,overflow:0,no_new_navigation:true,real_acoustic_authority:true},null,2));
console.log(`${scenarios.length} real acoustic authority browser flows passed; failed qualification enforced; no external requests/errors/overflow.`);
} finally {await browser.close();}
