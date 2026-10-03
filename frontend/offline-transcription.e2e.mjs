import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from 'playwright-core';
const base='http://127.0.0.1:5589/';
const root=new URL('../.var/phase8/browser-fixture/',import.meta.url).pathname;
const executor=join(root,'executor');
const screenshot=join(root,'screenshots');mkdirSync(screenshot,{recursive:true});
const info=JSON.parse(readFileSync(join(root,'fixture.json')));
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const errors=[],external=[],scenarios=[];
const wav=(value)=>{const b=Buffer.alloc(64044);b.write('RIFF');b.writeUInt32LE(b.length-8,4);b.write('WAVEfmt ',8);b.writeUInt32LE(16,16);b.writeUInt16LE(1,20);b.writeUInt16LE(1,22);b.writeUInt32LE(16000,24);b.writeUInt32LE(32000,28);b.writeUInt16LE(2,32);b.writeUInt16LE(16,34);b.write('data',36);b.writeUInt32LE(64000,40);for(let i=44;i<b.length;i+=2)b.writeInt16LE(value,i);return b;};
let index=Date.now() % 24000;
try {
for(const language of ['zh-CN','en']) for(const width of [320,768,1024,1440]) {
 const page=await browser.newPage({viewport:{width,height:1000}});
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('console',m=>{if(['error','warning'].includes(m.type()))errors.push(m.text());});
 page.on('request',r=>{if(!r.url().startsWith(base))external.push(r.url());});
 await page.addInitScript(lang=>localStorage.setItem('yia.ui-language',lang),language);
 const text=(en,zh)=>language==='en'?en:zh;
 const noOverflow=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`${language}/${width} overflow`);
 await page.goto(base+'#Following');
 await page.getByRole('button',{name:text('Add Source','添加关注'),exact:true}).first().click();
 await page.getByRole('button',{name:text('Local files','本地文件'),exact:true}).click();
 const dialog=page.getByRole('dialog');
 await dialog.getByLabel(text('Choose local files','选择本地文件')).setInputFiles({name:`离线媒体-${++index}.wav`,mimeType:'audio/wav',buffer:wav(index)});
 await dialog.getByRole('button',{name:text('Confirm import','确认导入'),exact:true}).click();
 await dialog.getByRole('link',{name:text('Open Content','打开内容'),exact:true}).click();
 const panel=page.getByRole('region',{name:text('Offline transcription','离线转写')});
 await panel.getByRole('button',{name:text('Start transcription','开始转写'),exact:true}).waitFor();
 await panel.locator('summary').click();
 for(const mode of ['RUNTIME_UNAVAILABLE','MODEL_MISSING','READY']) {
  writeFileSync(join(executor,'capability-mode.txt'),mode);
  await panel.getByRole('button',{name:text('Check availability','检查可用性'),exact:true}).click();
  if(mode==='READY')await panel.getByRole('button',{name:text('Start transcription','开始转写'),exact:true}).waitFor();
  else {await panel.getByRole('status').filter({hasText: mode==='MODEL_MISSING'?text('Local model is missing','缺少本地模型'):text('Local transcription is unavailable','本地转写暂不可用')}).waitFor();assert.equal(await panel.getByRole('button',{name:text('Start transcription','开始转写'),exact:true}).count(),0);}
  await noOverflow();await page.screenshot({path:join(screenshot,`${language}-${width}-${mode}.png`),fullPage:true});
 }
 writeFileSync(join(executor,'result-mode.txt'),'failure');
 await panel.getByRole('button',{name:text('Start transcription','开始转写'),exact:true}).click();
 await panel.getByRole('button',{name:text('Retry transcription','重试转写'),exact:true}).waitFor();
 await page.locator('.local-media-meta').getByText(text('Local transcription failed','本地转写失败'),{exact:true}).waitFor();
 assert.ok(!(await page.locator('body').innerText()).includes('/Users/'));
 writeFileSync(join(executor,'result-mode.txt'),'slow');
 await panel.getByRole('button',{name:text('Retry transcription','重试转写'),exact:true}).click();
 await panel.getByRole('status').filter({hasText:text('Transcribing…','正在转写…')}).waitFor();
 await page.locator('.local-media-meta').getByText(text('Transcribing…','正在转写…'),{exact:true}).waitFor();
 assert.equal(await page.locator('.local-transcription + .semantic-state').count(),0);
 await noOverflow();await page.screenshot({path:join(screenshot,`${language}-${width}-running.png`),fullPage:true});
 await page.locator('.timed-transcript li').first().waitFor();
 await page.locator('[id^="content-evidence-"]').first().waitFor();
 assert.ok((await page.locator('.timed-transcript').innerText()).includes('0.125s'));
 await panel.getByRole('status').filter({hasText:text('Transcription complete','转写完成')}).waitFor();
 await noOverflow();await page.screenshot({path:join(screenshot,`${language}-${width}-ready.png`),fullPage:true});
 const mediaId=page.url().split('#Content/')[1];
 await page.reload();await page.locator('.timed-transcript li').first().waitFor();
 assert.equal(await page.locator('.sidebar-nav button').count(),6);
 // Normal selected-Content Research accepts YouTube + Local text + Local timed media.
 const imported=await page.request.post(base+'api/v1/local/imports?filename=matrix-notes.md',{data:Buffer.from('Sentence1 local research source.\n'),headers:{'Content-Type':'application/octet-stream','X-YIA-Request':'local-ui'}});assert.ok(imported.ok());
 await page.getByRole('navigation').getByRole('button',{name:text('Intelligence','洞察'),exact:true}).click();
 await page.getByRole('button',{name:text('Research','研究'),exact:true}).click();
 await page.getByRole('button',{name:text('New Research','新建研究'),exact:true}).click();
 await page.getByLabel(text('Research question','研究问题')).fill('sentence1 mixed timed sources');
 await page.getByRole('checkbox',{name:`离线媒体-${index}.wav`,exact:false}).check();
 await page.getByRole('checkbox',{name:/matrix-notes.md/}).check();
 const video=await (await page.request.get(base+'api/v1/videos/'+info.content_id)).json();
 await page.getByRole('checkbox',{name:new RegExp(video.video.title.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'))}).check();
 await page.getByRole('button',{name:text('Assemble library packet','收集资料库证据包'),exact:true}).click();
 await page.locator('.research-result blockquote').first().waitFor();
 const result=await page.locator('.research-result').innerText();assert.ok(result.includes('YouTube')&&result.includes(text('Local','本地'))&&result.includes('本地离线'));
 await noOverflow();await page.screenshot({path:join(screenshot,`${language}-${width}-research.png`),fullPage:true});
 scenarios.push({language,width,mediaId,states:['runtime absent','model missing','ready','failure','retry','running','timed transcript','Summary','Evidence','reload','mixed Research']});
 await page.close();
}
assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
writeFileSync(join(root,'browser-report.json'),JSON.stringify({scenarios,errors,external,overflow:0,nativeModelValidation:false},null,2));
console.log(`${scenarios.length} Phase 8 live HTTP/SQLite browser matrix flows passed.`);
}finally {await browser.close();}
