import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {chromium} from '../../../frontend/node_modules/playwright-core/index.mjs';
const base='http://127.0.0.1:18977/';
const output=new URL('.',import.meta.url).pathname;
const runtime=new URL('../../../.var/d2-01/',import.meta.url).pathname;
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const errors=[],external=[],scenarios=[],expectedConsole=[];
const observe = page => {
 page.on("pageerror", error => errors.push(String(error)));
 page.on("console", message => {
  if (!["error", "warning"].includes(message.type())) return;
  if (message.text().includes("status of 422")) expectedConsole.push(message.text());
  else errors.push(message.text());
 });
 page.on("request", request => { if (!request.url().startsWith(base)) external.push(request.url()); });
};
try {
 let sequence=0;
 for(const language of ['en','zh-CN']) {
  for(const width of [1440,320]) {
   const page=await browser.newPage({viewport:{width,height:1000}});
   const t=(en,zh)=>language==='en'?en:zh;
   observe(page);
   await page.addInitScript(lang=>localStorage.setItem('yia.ui-language',lang),language);
   await page.goto(base+'#Following');
   await page.getByRole('button',{name:t('Following','关注'),exact:true}).click();
   await page.getByRole('button',{name:t('Add Source','添加关注'),exact:true}).first().click();
   await page.getByRole('button',{name:t('Import local file','导入本地文件')}).click();
   const filename=`d2-video-${sequence++}.mp4`;
   await page.getByLabel(t('Choose local files','选择本地文件')).setInputFiles(runtime+filename);
   // Returning from the native chooser produces focus. Refresh runs against the real API.
   let refreshed=page.waitForResponse(r=>r.url().endsWith('/sources')&&r.request().method()==='GET');
   await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
   await refreshed;
   await page.getByRole('heading',{name:t('Add local files','添加本地文件')}).waitFor();
   assert.equal(await page.getByText(filename,{exact:true}).count(),1);
   const dialog=page.getByRole('dialog');
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   assert.equal(await dialog.evaluate(el=>el.scrollWidth>el.clientWidth),false);
   // Hold a real request to inspect uploading state and exercise the second refresh boundary.
   let release;const gate=new Promise(resolve=>release=resolve);
   let receipt;
   await page.route('**/api/v1/local/imports?*',async route=>{await gate;const result=await route.fetch();receipt={status:result.status(),body:await result.json()};await route.fulfill({response:result})});
   const uploads=[];page.on('request',r=>{if(r.url().includes('/local/imports')&&r.method()==='POST')uploads.push(r.url())});
   const confirm=page.getByRole('button',{name:t('Confirm import','确认导入')});
   const accepted=page.waitForResponse(r=>r.url().includes('/local/imports')&&r.request().method()==='POST');
   await confirm.focus();await page.keyboard.press('Enter');
   await page.getByText(t('Importing selected files…','正在导入所选文件…'),{exact:true}).waitFor();
   assert.equal(await confirm.isDisabled(),true);
   assert.equal(await page.getByRole('button',{name:t('Cancel','取消'),exact:true}).isDisabled(),true);
   refreshed=page.waitForResponse(r=>r.url().endsWith('/sources')&&r.request().method()==='GET');
   await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await refreshed;
   await page.screenshot({path:output+`uploading-${language}-${width}.png`});
   assert.equal(await page.getByRole('heading',{name:t('Add local files','添加本地文件')}).count(),1);
   await page.keyboard.press('Enter');
   assert.equal(uploads.length,1);
   release();
   const result=await accepted; assert.equal(result.status(),201);
   const imported=receipt.body.import;
   assert.equal(imported.filename,filename);assert.equal(imported.status,'TRANSCRIPTION_UNAVAILABLE');
   await page.getByRole('heading',{name:t('Content','内容'),exact:true}).waitFor();
   await page.getByRole('heading',{name:filename,exact:true}).waitFor();
   assert.equal(await page.getByRole('dialog').count(),0);
   await page.getByText(t('File imported. Its processing status appears below.','文件已导入。处理状态显示在下方。'),{exact:true}).waitFor();
   await page.getByRole('region',{name:t('Offline transcription','离线转写')}).waitFor();
   await page.getByText(t('Provide a local MLX Whisper model directory to enable offline transcription. No model is downloaded automatically.','配置本机已有的 MLX Whisper 模型目录即可启用离线转写。不会自动下载模型。'),{exact:true}).waitFor();
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   const detail=await page.request.get(base+`api/v1/videos/${imported.content_id}`);
   const dto=await detail.json();assert.equal(dto.video.filename,filename);assert.equal(dto.transcript.status,'TRANSCRIPTION_UNAVAILABLE');
   assert.equal(dto.note.v2.status,'UNAVAILABLE');assert.equal(dto.intelligence_result.status,'NOT_PROCESSED');
   await page.screenshot({path:output+`content-${language}-${width}.png`});
   await page.reload();
   await page.getByRole('button',{name:new RegExp(filename.replace('.','\\.'))}).waitFor();
   assert.equal(uploads.length,1);
   scenarios.push({language,width,filename,content_id:imported.content_id,post_status:result.status(),processing:imported.status,selection_survived_focus:true,upload_survived_focus:true,keyboard_confirm:true,double_submit_guard:true,automatic_content:true,reload_list:true,no_overflow:true});
   await page.close();
  }
  const page=await browser.newPage({viewport:{width:320,height:1000}});
  observe(page);
  const t=(en,zh)=>language==='en'?en:zh;
  await page.addInitScript(lang=>localStorage.setItem('yia.ui-language',lang),language);
  for(const kind of ['txt','md','wav','invalid']) {
   await page.goto(base+'#Following');
   await page.getByRole('button',{name:t('Following','关注'),exact:true}).click();
   await page.getByRole('button',{name:t('Add Source','添加关注'),exact:true}).first().click();
   await page.getByRole('button',{name:t('Import local file','导入本地文件')}).click();
   const filename=`d2-${language}-${kind}.${kind==='invalid'?'mp4':kind}`;
   const buffer=kind==='wav'?readFileSync(runtime+`d2-audio-${language}.wav`):Buffer.from(kind==='invalid'?'bad synthetic media':`D2 ${language} ${kind} evidence. Local content only.\n`);
   await page.getByLabel(t('Choose local files','选择本地文件')).setInputFiles({name:filename,mimeType:'application/octet-stream',buffer});
   const accepted=page.waitForResponse(r=>r.url().includes('/local/imports')&&r.request().method()==='POST');
   await page.getByRole('button',{name:t('Confirm import','确认导入')}).click();
   const result=await accepted;
   if(kind==='invalid') {
    assert.equal(result.status(),422);
    await page.getByRole('alert').waitFor();
    assert.match(await page.getByRole('alert').innerText(),t(/malformed/,/损坏/));
    assert.equal(await page.getByRole('button',{name:t('Retry failed files','重试失败的文件')}).count(),1);
    assert.equal(await page.getByRole('heading',{name:t('Add local files','添加本地文件')}).count(),1);
    await page.screenshot({path:output+`failure-${language}.png`});
   } else {
    assert.equal(result.status(),201);
    const imported=(await result.json()).import;
    assert.equal(imported.status,kind==='wav'?'TRANSCRIPTION_UNAVAILABLE':'READY');
    await page.getByRole('heading',{name:filename,exact:true}).waitFor();
    assert.equal(await page.getByRole('dialog').count(),0);
   }
   scenarios.push({language,width:320,kind,filename,post_status:result.status(),real_api:true});
  }
  await page.close();
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 writeFileSync(output+'browser-validation.json',JSON.stringify({scenarios,errors,external,expectedConsole,fixture:'ffmpeg-generated media; real normal composition; no credentials; no transcription model'},null,2));
 console.log(`${scenarios.length} real browser scenarios passed, zh/en desktop/320px, focus refresh, keyboard, errors and all local formats`);
}finally{await browser.close()}
