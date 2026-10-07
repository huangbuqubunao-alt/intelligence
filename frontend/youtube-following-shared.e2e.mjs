import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {chromium} from 'playwright-core';
const base='http://127.0.0.1:5713/',errors=[],external=[],scenarios=[];
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
try {
 for(const language of ['zh-CN','en']) {
  const t=(en,zh)=>language==='en'?en:zh;
  const page=await browser.newPage({viewport:{width:320,height:1000}});
  page.setDefaultTimeout(30000);
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('console',m=>{if(['error','warning'].includes(m.type()))errors.push(m.text());});
  page.on('request',r=>{if(!r.url().startsWith(base))external.push(r.url());});
  await page.addInitScript(lang=>localStorage.setItem('yia.ui-language',lang),language);
  const staleResponse=page.waitForResponse(r=>r.url().endsWith('/api/v1/sources/check-stale')&&r.status()===202);
  await page.goto(base+'#Following');await staleResponse;
  for(let attempt=0;attempt<60;attempt++){const response=await page.request.get(base+'api/v1/sources');const sources=(await response.json()).sources;if(sources.every(s=>!s.tracking?.checking))break;if(attempt===59)assert.fail('Lifecycle checks did not settle');await page.waitForTimeout(500);}
  const filter=page.getByLabel(t('Following filter','筛选关注'));
  await filter.selectOption('updates');
  await page.locator('[data-source-id="youtube-channel-UC0000000000000000000000"]').waitFor();
  assert.equal(await page.locator('[data-source-id="bilibili-creator-123"]').count(),0);
  await filter.selectOption('attention');
  for(const id of ['youtube-channel-UC0000000000000000000000','bilibili-creator-123'])await page.locator(`[data-source-id="${id}"]`).waitFor();
  await filter.selectOption('insights');assert.equal(await page.locator('.source-row').count(),0);
  await filter.selectOption('all');
  for(const [id,kind] of [['youtube-channel-UC0000000000000000000000','channel'],['bilibili-creator-123','creator']]) {
   const source=async()=>{const r=await page.request.get(base+'api/v1/sources/'+id);assert.equal(r.status(),200);return(await r.json()).source;};
   const before=await source();
   await page.locator(`[data-source-id="${id}"] .source-select`).click();
   let dialog=page.getByRole('dialog',{name:kind==='channel'?t('Channel Following','频道关注'):t('Creator Following','UP 主关注')});
   await dialog.getByRole('button',{name:t('Check Now','立即检查'),exact:true}).waitFor();
   if(kind==='creator'){assert.equal(await dialog.getByRole('button',{name:t('Check Now','立即检查'),exact:true}).isDisabled(),true);await dialog.getByText(t('Continuous creator tracking is currently unavailable','UP 主持续关注当前暂不可用'),{exact:true}).waitFor();}
   await dialog.getByRole('button',{name:t('Pause monitoring','暂停监测'),exact:true}).click();
   await dialog.getByRole('button',{name:t('Resume monitoring','继续关注'),exact:true}).waitFor();
   await dialog.getByRole('button',{name:t('Close','关闭'),exact:true}).click();
   await filter.selectOption('paused');await page.locator(`[data-source-id="${id}"]`).waitFor();
   await page.locator(`[data-source-id="${id}"] .source-select`).click();
   dialog=page.getByRole('dialog');await dialog.getByRole('button',{name:t('Resume monitoring','继续关注'),exact:true}).waitFor();
   assert.equal(await dialog.getByRole('button',{name:t('Check Now','立即检查'),exact:true}).isDisabled(),true);
   await dialog.getByRole('button',{name:t('Resume monitoring','继续关注'),exact:true}).click();
   await dialog.getByRole('button',{name:t('Pause monitoring','暂停监测'),exact:true}).waitFor();
   await dialog.getByRole('button',{name:t('Close','关闭'),exact:true}).click();await filter.selectOption('all');
   const after=await source();assert.equal(after.enabled,true);assert.equal(after.tracking.verified_at,before.tracking.verified_at);assert.equal(after.tracking.update_count,before.tracking.update_count);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  }
  scenarios.push({language,width:320,providers:['YOUTUBE','BILIBILI'],filters:['all','updates','attention','insights','paused'],shared_detail:true,pause_blocks_check:true,resume_preserves_frontier:true});await page.close();
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 writeFileSync(new URL('../docs/validation/phase12-resume/shared-ui-browser.json',import.meta.url),JSON.stringify({scenarios,errors,external},null,2)+'\n');console.log('2 bilingual cross-provider detail/filter flows passed');
} finally {await browser.close();}
