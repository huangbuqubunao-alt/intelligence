import {chromium} from '../../../../frontend/node_modules/playwright-core/index.mjs';
import {writeFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const root='docs/validation/muse-final-audit',base='http://127.0.0.1:5688/';
const ctx=await chromium.launchPersistentContext('.var/muse-final-audit/gui/settings-profile',{executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,viewport:{width:1440,height:1200},acceptDownloads:true});const page=ctx.pages()[0],errors=[];page.on('pageerror',e=>errors.push(String(e)));
try{
await page.goto(base);await page.waitForLoadState('networkidle');if(await page.getByRole('button',{name:'暂时跳过',exact:true}).count())await page.getByRole('button',{name:'暂时跳过',exact:true}).click();await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'编辑语言',exact:true}).waitFor();await page.screenshot({path:root+'/screenshots/10-settings-ready-zh.png',fullPage:true});
await page.getByRole('button',{name:'编辑语言',exact:true}).click();await page.getByLabel('界面语言',{exact:true}).selectOption('en');await page.getByLabel('默认输出语言',{exact:true}).selectOption('en');await page.getByRole('button',{name:'保存语言',exact:true}).click();await page.getByRole('button',{name:'Edit language',exact:true}).waitFor();await page.screenshot({path:root+'/screenshots/11-settings-en.png',fullPage:true});
await page.getByRole('button',{name:'Create Backup',exact:true}).click();await page.getByRole('link',{name:'Save backup file',exact:true}).waitFor();await page.screenshot({path:root+'/screenshots/12-backup-created.png',fullPage:true});
const downloadPromise=page.waitForEvent('download');await page.getByRole('link',{name:'Save backup file',exact:true}).click();const download=await downloadPromise;const archive='.var/muse-final-audit/gui/gui-backup.zip';await download.saveAs(archive);
await page.getByLabel('Choose backup file',{exact:true}).setInputFiles(archive);await page.getByRole('button',{name:'Restore this backup…',exact:true}).waitFor();await page.screenshot({path:root+'/screenshots/13-restore-preview.png',fullPage:true});
await page.getByRole('button',{name:'Restore this backup…',exact:true}).click();await page.getByLabel('Type RESTORE to confirm',{exact:true}).fill('RESTORE');await page.screenshot({path:root+'/screenshots/14-restore-confirm.png'});await page.getByRole('button',{name:'Confirm Restore and restart',exact:true}).click();
await page.waitForTimeout(1200);console.log('RESTORE_STATE',await page.locator('body').innerText());
writeFileSync(root+'/gui-settings.json',JSON.stringify({zhAndEn:true,backupCreated:true,backupDownloaded:true,restoreStaged:true,restoreConfirmed:true,archive,errors},null,2)+'\n');
}finally{await ctx.close()}
