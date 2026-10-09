import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {chromium} from '../../../frontend/node_modules/playwright-core/index.mjs';
const base='http://127.0.0.1:18966/';
const output=new URL('.',import.meta.url).pathname;
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const errors=[],external=[],scenarios=[];
try {
 for(const language of ['en','zh-CN']) {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const t=(en,zh)=>language==='en'?en:zh;
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('console',m=>{if(['error','warning'].includes(m.type()))errors.push(m.text());});
  page.on('request',r=>{if(!r.url().startsWith(base))external.push(r.url());});
  await page.addInitScript(lang=>localStorage.setItem('yia.ui-language',lang),language);
  await page.goto(base);
  if(await page.getByRole('button',{name:t('Skip for now','暂时跳过')}).isVisible()) await page.getByRole('button',{name:t('Skip for now','暂时跳过')}).click();
  await page.getByRole('button',{name:t('Settings','设置'),exact:true}).click();
  await page.getByRole('button',{name:t('Edit language','编辑语言')}).waitFor();
  assert.equal(await page.getByLabel(t('Preferred output language','默认输出语言')).count(),0);
  const advanced=page.getByText(t('Advanced and diagnostics','高级设置与诊断'),{exact:true});
  assert.equal(await advanced.evaluate(el=>el.parentElement.open),false);
  for(const width of [320,1440]) {
   await page.setViewportSize({width,height:1000});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Settings width');
   assert.equal(await page.getByRole("heading",{name:t("Settings","设置"),exact:true}).count(),1);
   assert.equal(await page.getByRole("navigation").count(),1);
   await page.screenshot({path:output+`settings-${language}-${width}.png`,fullPage:false});
   scenarios.push({language,width,settings_compact:true,no_overflow:true});
  }
  await page.getByRole('button',{name:t('Edit language','编辑语言')}).click();
  await page.getByRole('button',{name:t('Save language','保存语言')}).click();
  await page.getByRole('button',{name:t('Edit language','编辑语言')}).waitFor();
  await page.getByRole('button',{name:t('Following','关注'),exact:true}).click();
  await page.getByRole('button',{name:t('Add Source','添加关注'),exact:true}).first().click();
  await page.getByLabel(t('Paste link','粘贴链接')).fill('https://www.youtube.com/@3blue1brown/videos');
  await page.getByRole('radio',{name:t(/^Organize content/,/^整理内容/)}).waitFor();
  assert.equal(await page.getByLabel(t('Monitor this Source','监测这个来源')).count(),0);
  for(const width of [320,1440]) {
   await page.setViewportSize({width,height:1000});
   const dialog=page.getByRole('dialog');
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Add page width');
   assert.equal(await dialog.evaluate(el=>el.scrollWidth>el.clientWidth),false,'Add dialog width');
   await page.screenshot({path:output+`add-${language}-${width}.png`,fullPage:false});
   scenarios.push({language,width,channel_videos_recognized:true,default_content_only:true,one_add_entry:true});
  }
  // Import real local bytes through the real supported UI/API.
  await page.getByRole('button',{name:t('Import local file','导入本地文件')}).click();
  await page.getByLabel(t('Choose local files','选择本地文件')).setInputFiles({name:`day1-${language}.txt`,mimeType:'text/plain',buffer:Buffer.from(`Local dogfood evidence ${language}. Content stays usable without cloud Intelligence.\n`)});
  await page.getByRole('button',{name:t('Confirm import','确认导入')}).click();
  await page.getByRole('link',{name:t('Open Content','打开内容')}).waitFor();
  await page.getByRole('link',{name:t('Open Content','打开内容')}).click();
  await page.getByText(`day1-${language}.txt`,{exact:true}).first().waitFor();
  await page.screenshot({path:output+`local-${language}.png`,fullPage:false});
  await page.close();
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 writeFileSync(output+'browser-validation.json',JSON.stringify({scenarios,local_imports:2,errors,external},null,2));
 console.log('Bilingual compact Settings, Add recognition, responsive layouts and real Local imports passed');
} finally {await browser.close();}
