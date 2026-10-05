import assert from 'node:assert/strict';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from 'playwright-core';
const base='http://127.0.0.1:5713/', root=new URL('../.var/phase12/browser/',import.meta.url).pathname;
const info=JSON.parse(readFileSync(join(root,'fixture.json'))), offline=process.env.YIA_PHASE12_OFFLINE==='1';
const evidence=new URL('../docs/validation/phase12/',import.meta.url).pathname;
mkdirSync(evidence,{recursive:true});mkdirSync(join(root,'screenshots'),{recursive:true});
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const errors=[],external=[],scenarios=[];
try{
 let index=0;
 for(const language of ['zh-CN','en'])for(const width of [320,768,1024,1440]){
  const i=index++,id='youtube-channel-'+info.channels[i],old='oldyt'+String(i).padStart(6,'0'),caption='ytcpt'+String(i).padStart(6,'0'),missing='ytnoo'+String(i).padStart(6,'0');
  const page=await browser.newPage({viewport:{width,height:1000}});page.setDefaultTimeout(30000);
  const t=(en,zh)=>language==='en'?en:zh;
  page.on('pageerror',e=>errors.push(String(e)));page.on('console',m=>{if(['error','warning'].includes(m.type()))errors.push(m.text());});page.on('request',r=>{if(!r.url().startsWith(base))external.push(r.url());});
  await page.addInitScript(lang=>localStorage.setItem('yia.ui-language',lang),language);
  const get=async path=>{const r=await page.request.get(base+'api/v1/'+path);assert.equal(r.status(),200);return r.json();};
  const post=async(path,data={})=>{const r=await page.request.post(base+'api/v1/'+path,{headers:{Origin:base.slice(0,-1),'X-YIA-Request':'local-ui'},data});assert.ok(r.ok(),await r.text());return r.json();};
  const advance=publish=>post('fixture/advance',{index:i,publish});
  const waitSource=async(sourceId,predicate)=>{let latest;for(let attempt=0;attempt<60;attempt++){latest=(await get('sources/'+sourceId)).source;if(predicate(latest))return latest;await page.waitForTimeout(500);}assert.fail(JSON.stringify({sourceId,latest}));};
  const noOverflow=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`${language}/${width}`);
  const following=()=>page.getByRole('navigation').getByRole('button',{name:t('Following','关注'),exact:true}).click();
  const detail=async()=>{await following();await page.locator(`[data-source-id="${id}"] .source-select`).click();return page.getByRole('dialog',{name:t('Channel Following','频道关注')});};
  await page.goto(base+'#Home');await page.locator('.knowledge-delta').waitFor();assert.equal(await page.locator('.sidebar-nav button').count(),6);
  if(!offline){
   const before=(await get('videos')).videos.length;
   await following();await page.getByRole('button',{name:t('Add Source','添加关注'),exact:true}).first().click();let dialog=page.getByRole('dialog');
   await dialog.getByLabel(t('Source URL','来源链接')).fill('https://youtube.com/@public'+i);await dialog.getByRole('button',{name:t('Add Source','添加关注'),exact:true}).click();await dialog.getByText(t('Use Follow a channel to follow from now on without importing existing videos.','请选择“关注一个频道”，从现在开始关注，不导入已有视频。'),{exact:true}).waitFor();
   await dialog.getByRole('button',{name:t('Follow a channel','关注一个频道'),exact:true}).click();await dialog.getByLabel(t('Channel URL, @handle or channel id','频道链接、@用户名或频道 ID')).fill('https://youtube.com/@public'+i);
   await dialog.getByRole('button',{name:t('Follow channel','关注频道'),exact:true}).click();await dialog.getByRole('button',{name:t('Done','完成'),exact:true}).click();
   assert.equal((await get('videos')).videos.length,before);assert.equal((await get('sources/'+id)).source.tracking.update_count,0);
   await page.goto(base+'#Content/'+old);await page.getByRole('button',{name:t('Follow this channel','关注此频道'),exact:true}).click();await page.getByText(t('Channel followed. Check Following for its starting point and source health.','已关注频道，请在关注详情中查看跟踪起点和来源状态。'),{exact:true}).waitFor();assert.equal((await get('sources')).sources.filter(s=>s.source_id===id).length,1);
   if(i===0)await post('sources/creators',{input:'123'});
   await advance(false);dialog=await detail();await dialog.getByRole('button',{name:t('Check Now','立即检查'),exact:true}).click();await waitSource(id,s=>Boolean(s.tracking.baseline_at)&&!s.tracking.checking);assert.equal((await get('sources/'+id)).source.tracking.update_count,0);await noOverflow();await dialog.getByRole('button',{name:t('Close','关闭'),exact:true}).click();
   await advance(true);dialog=await detail();await dialog.getByRole('button',{name:t('Check Now','立即检查'),exact:true}).click();await waitSource(id,s=>s.tracking.update_count===2&&!s.tracking.checking);await dialog.getByRole('link',{name:new RegExp(missing)}).waitFor();await noOverflow();await page.screenshot({path:join(root,'screenshots',`${language}-${width}-following.png`),fullPage:true});
   await dialog.getByRole('button',{name:t('Pause monitoring','暂停监测'),exact:true}).click();await dialog.getByRole('button',{name:t('Resume monitoring','继续关注'),exact:true}).waitFor();assert.equal((await get('sources/'+id)).source.enabled,false);await dialog.getByRole('button',{name:t('Resume monitoring','继续关注'),exact:true}).click();await dialog.getByRole('button',{name:t('Pause monitoring','暂停监测'),exact:true}).waitFor();await dialog.getByRole('button',{name:t('Close','关闭'),exact:true}).click();
   const filter=page.getByLabel(t('Following filter','筛选关注'));await filter.selectOption('updates');assert.ok(await page.getByText('YouTube channel '+i,{exact:true}).count());await filter.selectOption('attention');assert.ok(await page.getByText('YouTube channel '+i,{exact:true}).count());await filter.selectOption('all');
   await post('sources/bilibili-creator-123/check',{command_id:crypto.randomUUID()});await waitSource('bilibili-creator-123',s=>s.tracking.update_count===1&&!s.tracking.checking);
  }else{
   const before=(await get('sources/'+id)).source;await advance(false);const dialog=await detail();await dialog.getByRole('button',{name:t('Check Now','立即检查'),exact:true}).click();await waitSource(id,s=>s.tracking.health==='OFFLINE'&&!s.tracking.checking);await dialog.getByText(t('Unable to connect. Your last successful check is preserved.','暂时无法连接，已保留上次成功检查的状态。'),{exact:true}).waitFor();const after=(await get('sources/'+id)).source;assert.equal(after.last_success_at,before.last_success_at);assert.equal(after.tracking.verified_at,before.tracking.verified_at);assert.equal(after.tracking.update_count,2);await noOverflow();await dialog.getByRole('button',{name:t('Close','关闭'),exact:true}).click();
  }
  await page.goto(base+'#Content/'+caption);await page.locator('.timed-transcript li').first().waitFor();await page.locator('[id^="content-evidence-"]').first().waitFor();await noOverflow();await page.screenshot({path:join(root,'screenshots',`${offline?'offline-':''}${language}-${width}-caption.png`),fullPage:true});assert.equal(await page.getByRole('button',{name:t('Transcribe on device','在设备上转写'),exact:true}).count(),0);
  await page.goto(base+'#Content/'+missing);await page.getByRole('button',{name:t('Follow this channel','关注此频道'),exact:true}).waitFor();assert.equal(await page.locator('.timed-transcript').count(),0);await noOverflow();
  await page.getByRole('navigation').getByRole('button',{name:t('Intelligence','洞察'),exact:true}).click();await page.getByRole('button',{name:t('Research','研究'),exact:true}).click();await page.getByRole('button',{name:t('New Research','新建研究'),exact:true}).click();await page.getByLabel(t('Research question','研究问题')).fill('public Sentence1');
  const contents=(await get('videos')).videos;for(const contentId of [caption,'bilibili-BV1xx411c7mE',info.local_id])await page.getByRole('checkbox',{name:new RegExp(contents.find(v=>v.video_id===contentId).title)}).check();await page.getByRole('button',{name:t('Assemble library packet','收集资料库证据包'),exact:true}).click();await page.locator('.research-result blockquote').first().waitFor();const research=await page.locator('.research-result').innerText();for(const label of ['YouTube',t('Bilibili','哔哩哔哩'),t('Local','本地')])assert.ok(research.includes(label));await noOverflow();
  await page.getByRole('navigation').getByRole('button',{name:t('Home','首页'),exact:true}).click();await page.locator('.knowledge-delta').waitFor();await noOverflow();scenarios.push({language,width,offline,source:id});await page.close();
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);writeFileSync(join(evidence,offline?'youtube-offline-browser.json':'youtube-browser.json'),JSON.stringify({scenarios,errors,external},null,2));console.log(`${scenarios.length} mixed-provider YouTube flows passed`);
}finally{await browser.close();}
