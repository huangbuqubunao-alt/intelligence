import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {chromium} from '/Users/developer/Documents/yia-worktrees/phase13-background-following/frontend/node_modules/playwright-core/index.mjs';
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const results=[];
try {
 for(const language of ['en','zh-CN']){
  const page=await browser.newPage({viewport:{width:320,height:1000}});
  await page.addInitScript(l=>localStorage.setItem('yia.ui-language',l),language);
  await page.goto('http://127.0.0.1:18866/#Settings');
  const t=(en,zh)=>language==='en'?en:zh;
  await page.getByRole('heading',{name:t('Backup and Restore','备份与恢复'),exact:true}).waitFor();
  const create=page.getByRole('button',{name:t('Create Backup','创建备份'),exact:true});
  await create.waitFor();
  await page.getByText(t('Core data is quiescent and ready for backup.','核心数据已就绪，可以创建备份。'),{exact:true}).waitFor();
  assert.equal(await create.isEnabled(),true);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.screenshot({path:`/tmp/intelligence-phase13-evidence/backup-${language}-320.png`,fullPage:true});
  results.push({language,width:320,create_enabled:true,quiescent:true});await page.close();
 }
 writeFileSync('/tmp/intelligence-phase13-evidence/browser-backup.json',JSON.stringify(results,null,2));console.log('Backup readiness is visible and usable in both languages');
}finally{await browser.close();}
