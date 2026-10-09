import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {chromium} from '../../../frontend/node_modules/playwright-core/index.mjs';
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const output=new URL('.',import.meta.url).pathname;
const results=[];
try {
 for (const language of ['en','zh-CN']) {
  const t=(en,zh)=>language==='en'?en:zh;
  const page=await browser.newPage({viewport:{width:320,height:1000}});
  await page.addInitScript(lang=>localStorage.setItem('yia.ui-language',lang),language);
  await page.goto('http://127.0.0.1:18966/#Content/aircAruvnKk');
  await page.getByRole('button',{name:t('Extract Intelligence','提炼为洞察'),exact:true}).waitFor();
  assert.equal(await page.getByRole('link',{name:t('Open original source','打开原始来源'),exact:true}).count()>=1,true);
  await page.getByRole('button',{name:t('Extract Intelligence','提炼为洞察'),exact:true}).click();
  await page.getByText(t('Cloud Intelligence is currently unavailable because the provider or its runtime credential is unavailable. Existing Summary and Evidence remain usable.','云端洞察当前不可用：服务商或运行环境中的凭据不可用。已有摘要和证据仍可正常使用。'),{exact:true}).waitFor();
  await page.getByRole('button',{name:t('Intelligence','洞察'),exact:true}).click();
  await page.getByText(t('Analysis activity','洞察处理进度'),{exact:true}).waitFor();
  await page.screenshot({path:output+`intelligence-waiting-${language}-320.png`});
  await page.getByRole('button',{name:t('Following','关注'),exact:true}).click();
  const row=page.locator('.source-row').filter({hasText:'3Blue1Brown'});
  await row.getByRole('button',{name:t('Pause following','暂停关注'),exact:true}).click();
  await row.getByRole('button',{name:t('Resume following','持续关注'),exact:true}).click();
  await row.getByRole('button',{name:t('Pause following','暂停关注'),exact:true}).waitFor();
  assert.equal(await page.getByRole('dialog').count(),0);
  await page.screenshot({path:output+`following-${language}-320.png`});
  results.push({language,manual_wait_visible:true,pause_resume_without_dialog:true,real_source_name:true});
  await page.close();
  const copy=await browser.newPage({viewport:{width:320,height:1000}});
  await copy.addInitScript(lang=>localStorage.setItem('yia.ui-language',lang),language);
  await copy.goto('http://127.0.0.1:18968/');
  await copy.getByRole('button',{name:t('Following','关注'),exact:true}).click();
  await copy.getByRole('button',{name:/@lingdujieshuo/}).click();
  const dialog=copy.getByRole('dialog',{name:'@lingdujieshuo'});
  await dialog.waitFor();
  assert.equal(await dialog.getByRole('button',{name:t('Close','关闭'),exact:true}).count(),1);
  assert.equal(await dialog.getByRole('status').count(),1);
  assert.equal(await dialog.getByRole('button',{name:t('Pause following','暂停关注')}).count(),0);
  await copy.screenshot({path:output+`owner-copy-legacy-${language}-320.png`});
  results.push({language,owner_copy_legacy_visible:true,explicit_needs_attention:true,no_silent_tracking:true,accessible_close:true});
  await copy.close();
 }
 writeFileSync(output+'browser-following-content.json',JSON.stringify({results},null,2));
 console.log('Real isolated manual waiting, named Following row pause/resume, bilingual owner-copy legacy inspection passed');
} finally {await browser.close();}
