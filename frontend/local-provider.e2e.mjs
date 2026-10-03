import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from 'playwright-core';
const base='http://127.0.0.1:5573/';
const root=new URL('../.var/phase7/browser-fixture/',import.meta.url).pathname;
const info=JSON.parse(readFileSync(join(root,'fixture.json')));
const screenshots=join(root,'screenshots');mkdirSync(screenshots,{recursive:true});
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const errors=[],external=[],scenarios=[];
const restartOnly=process.env.YIA_PHASE7_RESTART_ONLY==='1';
const filename='本地研究-'+ 'long-filename-'.repeat(15)+'.md';
const source=Buffer.from('# Sentence1 local research\nSentence1 source evidence stays on device.\n<script>alert("never execute")</script>\n');
try {
for(const language of ['zh-CN','en']) for(const width of [320,768,1024,1440]){
 const page=await browser.newPage({viewport:{width,height:1000}});
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('console',m=>{if(['error','warning'].includes(m.type()))errors.push(m.text());});
 page.on('request',r=>{if(!r.url().startsWith(base))external.push(r.url());});
 page.on('dialog',async d=>{errors.push('Imported script executed');await d.dismiss();});
 await page.addInitScript(lang=>localStorage.setItem('yia.ui-language',lang),language);
 const text=(en,zh)=>language==='en'?en:zh;
 const get=async path=>{const r=await page.request.get(`${base}api/v1/${path}`);assert.equal(r.status(),200);return r.json();};
 const noOverflow=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`${language}/${width} overflow`);
 await page.goto(base+'#Home');await page.locator('.knowledge-delta').waitFor();assert.equal(await page.locator('.sidebar-nav button').count(),6);
 if(!restartOnly){
  await page.getByRole('navigation').getByRole('button',{name:text('Following','关注'),exact:true}).click();
  await page.getByRole('button',{name:text('Add Source','添加关注'),exact:true}).first().click();
  await page.getByRole('button',{name:text('Local files','本地文件'),exact:true}).click();
  const dialog=page.getByRole('dialog');const picker=dialog.getByLabel(text('Choose local files','选择本地文件'));
  await picker.setInputFiles({name:'unsupported.pdf',mimeType:'application/pdf',buffer:Buffer.from('pdf')});await dialog.getByRole('alert').waitFor();
  assert.equal(await dialog.getByRole('button',{name:text('Confirm import','确认导入'),exact:true}).isDisabled(),true);
  await picker.setInputFiles({name:filename,mimeType:'text/markdown',buffer:source});await noOverflow();
  await dialog.getByRole('button',{name:text('Confirm import','确认导入'),exact:true}).click();
  const open=dialog.getByRole('link',{name:text('Open Content','打开内容'),exact:true});await open.waitFor();
  assert.ok((await dialog.innerText()).includes(text('Ready','就绪')));
  await page.screenshot({path:join(screenshots,`${language}-${width}-import.png`),fullPage:true});await open.click();
 }else{const local=(await get('videos')).videos.find(c=>c.provider==='LOCAL');assert.ok(local);await page.goto(base+'#Content/'+local.video_id);}
 await page.locator('[id^="content-evidence-"]').first().waitFor();
 const body=await page.locator('body').innerText();assert.ok(body.includes(text('Local','本地'))&&body.includes(text('Lines','行'))&&body.includes('Sentence1 source evidence stays on device.'));await noOverflow();
 await page.screenshot({path:join(screenshots,`${restartOnly?'restart-':''}${language}-${width}-content.png`),fullPage:true});
 const route=page.url();await page.reload();await page.locator('[id^="content-evidence-"]').first().waitFor();assert.equal(page.url(),route);
 await page.getByRole('navigation').getByRole('button',{name:text('Content','内容'),exact:true}).click();
 const contents=(await get('videos')).videos;assert.ok(contents.some(c=>c.provider==='YOUTUBE')&&contents.some(c=>c.provider==='LOCAL'));await noOverflow();
 await page.getByRole('navigation').getByRole('button',{name:text('Following','关注'),exact:true}).click();await page.getByText(text('Local library','本地资料库'),{exact:true}).first().waitFor();await noOverflow();
 await page.getByRole('navigation').getByRole('button',{name:text('Intelligence','洞察'),exact:true}).click();await page.getByRole('button',{name:text('Research','研究'),exact:true}).click();
 for(const mixed of [false,true]){
  await page.getByRole('button',{name:text('New Research','新建研究'),exact:true}).click();
  await page.getByLabel(text('Research question','研究问题')).fill(mixed?'sentence1 mixed sources':'sentence1 local only');
  await page.getByRole('checkbox',{name:/本地研究-/}).check();
  if(mixed){const title=(await get('videos/'+info.content_id)).video.title;await page.getByRole('checkbox',{name:new RegExp(title.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'))}).check();}
  await page.getByRole('button',{name:text('Assemble library packet','收集资料库证据包'),exact:true}).click();await page.locator('.research-result blockquote').first().waitFor();
  const result=await page.locator('.research-result').innerText();assert.ok(result.includes(text('Local','本地')));if(mixed)assert.ok(result.includes('YouTube'));await noOverflow();
  await page.screenshot({path:join(screenshots,`${restartOnly?'restart-':''}${language}-${width}-${mixed?'mixed':'local'}-research.png`),fullPage:true});
  await page.getByRole('button',{name:text('Open Content and Evidence','打开内容与证据'),exact:true}).first().click();await page.locator('[id^="content-evidence-"]').first().waitFor();
  await page.getByRole('button',{name:text('Back to Research','返回研究'),exact:true}).click();await page.locator('.research-result blockquote').first().waitFor();
 }
 await page.getByRole('navigation').getByRole('button',{name:text('Home','首页'),exact:true}).click();await page.locator('.knowledge-delta').getByText(filename,{exact:true}).waitFor();assert.ok((await page.locator('.knowledge-delta').innerText()).includes('本地研究-'));await noOverflow();
 scenarios.push(`${restartOnly?'restart/':''}${language}/${width}: picker adapter/import/errors/dedupe/Content/Summary/Evidence/mixed library/Local+mixed Research/Delta`);await page.close();
}
assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
writeFileSync(join(root,restartOnly?'local-restart-report.json':'local-browser-report.json'),JSON.stringify({scenarios,errors,external,overflow:0,nativePicker:'File adapter; OS dialog not driven'},null,2));
console.log(`${scenarios.length} Local multi-source real HTTP/SQLite UI flows passed.`);
}finally{await browser.close();}
