import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {chromium} from '/Users/hua/Documents/yia-worktrees/phase13-background-following/frontend/node_modules/playwright-core/index.mjs';
const base='http://127.0.0.1:18866/',root='/tmp/intelligence-phase13-evidence/',errors=[],external=[],scenarios=[];
const id='youtube-channel-UCLA_DiR1FfKNvjuUpBHmylQ';
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
try {
 for (const language of ['en','zh-CN']) {
  const t=(en,zh)=>language==='en'?en:zh;
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  page.setDefaultTimeout(15000);
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('console',m=>{if(['error','warning'].includes(m.type())) errors.push(m.text());});
  page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('ws://127.0.0.1:18866/'))external.push(r.url());});
  await page.addInitScript(lang=>localStorage.setItem('yia.ui-language',lang),language);
  await page.goto(base+'#Following');
  await page.locator(`[data-source-id="${id}"] .source-select`).click();
  const dialog=page.getByRole('dialog',{name:t('Channel Following','频道关注')});
  await dialog.getByText(t('Next automatic check','下次自动检查'),{exact:true}).waitFor();
  await dialog.getByText(t('Updates are checked automatically while the app is running.','应用运行时会自动检查更新。'),{exact:true}).waitFor();
  const retry=dialog.getByRole('button',{name:t('Retry','重试'),exact:true});
  assert.equal(await retry.isEnabled(),true,'manual network retry remains available');
  for(const width of [320,768,1024,1440]){
   await page.setViewportSize({width,height:1000});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   assert.equal(await dialog.evaluate(el=>el.scrollWidth>el.clientWidth),false);
   await page.screenshot({path:root+`following-${language}-${width}.png`,fullPage:true});
   scenarios.push({language,width,real_sources_loaded:true,automatic_status:true,offline_manual_retry_enabled:true,no_horizontal_overflow:true});
  }
  await dialog.getByRole('button',{name:t('Pause monitoring','暂停监测'),exact:true}).click();
  await dialog.getByRole('button',{name:t('Resume monitoring','继续关注'),exact:true}).waitFor();
  assert.equal(await retry.isDisabled(),true);
  await dialog.getByRole('button',{name:t('Resume monitoring','继续关注'),exact:true}).click();
  await dialog.getByRole('button',{name:t('Pause monitoring','暂停监测'),exact:true}).waitFor();
  await dialog.getByRole('button',{name:t('Close','关闭'),exact:true}).click();
  await page.close();
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 writeFileSync(root+'browser-validation.json',JSON.stringify({scenarios,pause_resume:true,errors,external},null,2));
 console.log('8 bilingual responsive Following views and pause/resume passed against the actual local API');
} finally {await browser.close();}
