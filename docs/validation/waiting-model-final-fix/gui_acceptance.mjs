import { chromium } from '../../../frontend/node_modules/playwright-core/index.mjs';
import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import assert from 'node:assert/strict';

const final=process.env.WAITING_MODEL_FINAL_GUI==='1';
const root='docs/validation/waiting-model-final-fix'+(final?'/final-gui':''), base=final?'http://127.0.0.1:5798/':'http://127.0.0.1:5788/';
const runtimeRoot='.var/waiting-model-final-fix/'+(final?'gui-final':'gui');
const fixture=process.cwd()+'/'+runtimeRoot+'/wait-note.txt';
mkdirSync(root+'/screenshots',{recursive:true});
writeFileSync(fixture,'# Waiting model acceptance\n\nThis is original Content for an isolated cancellation test. Its source and Evidence must remain unchanged when extraction is cancelled.\n');
const context=await chromium.launchPersistentContext(runtimeRoot+'/chrome-profile',{
  executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:false,
  viewport:{width:1440,height:1080},acceptDownloads:true,
});
const page=context.pages()[0], errors=[], posts=[], result={realMacOS:process.platform==='darwin',headless:false};
page.on('pageerror',e=>errors.push(String(e)));
page.on('request',r=>{if(r.method()==='POST')posts.push({url:r.url().replace(/\/picks\/[^/]+/,'/picks/<grant>'),body:r.postData()})});
const shot=async name=>page.screenshot({path:root+'/screenshots/'+name+'.png',fullPage:true});
const snapshot=()=>JSON.parse(execFileSync('.venv/bin/python',['docs/validation/waiting-model-final-fix/gui_snapshot.py'],{encoding:'utf8'}));
try {
  await page.addInitScript(()=>localStorage.setItem('yia.ui-language','zh-CN'));
  await page.goto(base);await page.waitForLoadState('networkidle');
  for(let i=0;i<2;i++)if(await page.getByRole('button',{name:'继续',exact:true}).count())await page.getByRole('button',{name:'继续',exact:true}).click();
  if(await page.getByRole('button',{name:'暂时跳过',exact:true}).count())await page.getByRole('button',{name:'暂时跳过',exact:true}).click();
  let saved;
  if (!process.env.GUI_NATIVE_ALREADY_VERIFIED) {
  await page.getByRole('button',{name:'关注',exact:true}).click();
  await page.getByRole('button',{name:'添加关注',exact:true}).first().click();
  await page.getByRole('button',{name:'导入本地文件',exact:true}).click();
  await page.getByRole('button',{name:'选择本地文件',exact:true}).click();
  await page.waitForTimeout(1200);
  execFileSync('/usr/sbin/screencapture',['-x',root+'/screenshots/01-macos-native-picker.png']);
  execFileSync('/usr/bin/osascript',['-e',`tell application "System Events"
    tell process "IntelligenceFilePicker"
      set frontmost to true
      keystroke "g" using {command down, shift down}
      delay 1
      set value of text field 1 of sheet 1 of window 1 to "${fixture}"
      delay 2
      key code 36
      delay 2
      click button "Open" of splitter group 1 of window 1
    end tell
  end tell`]);
  await page.getByRole('button',{name:'确认导入',exact:true}).waitFor({timeout:30000});
  await shot('02-native-selected');
  await page.getByRole('button',{name:'确认导入',exact:true}).click();
  await page.waitForURL(/#Content\//,{timeout:60000});
  await page.getByRole('heading',{name:'wait-note.txt',exact:true}).waitFor();
  saved=page.url();result.contentUrl=saved;result.realAppKitImport=true;
  await page.reload();await page.getByRole('heading',{name:'wait-note.txt',exact:true}).waitFor();
  await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'创建备份',exact:true}).waitFor();
  await page.goBack();await page.getByRole('heading',{name:'wait-note.txt',exact:true}).waitFor();
  await page.goForward();await page.getByRole('button',{name:'创建备份',exact:true}).waitFor();
  await page.goto(saved);await page.getByRole('heading',{name:'wait-note.txt',exact:true}).waitFor();
  result.contentDeepLinkReloadBackForward=true;

  }
  // Existing product supports manual extraction only for verified YouTube Content.
  // This video was imported through the real UI; no fixtures or model result injection.
  saved=base+'#Content/aircAruvnKk';
  await page.goto(saved);await page.getByRole('button',{name:'提炼为洞察',exact:true}).waitFor({timeout:60000});
  result.contentUrl=saved;
  await page.getByRole('button',{name:'提炼为洞察',exact:true}).click();
  await page.getByText('当前没有合格的洞察模型。',{exact:true}).waitFor({timeout:30000});
  await page.getByRole('button',{name:'取消本次提炼',exact:true}).scrollIntoViewIfNeeded();
  await shot('03-waiting-model');
  const contentId=decodeURIComponent(saved.split('#Content/')[1]);
  const waiting=(await (await page.request.get(base+'api/v1/videos/'+contentId)).json()).waiting_model_executions;
  assert.equal(waiting.length,1);assert.equal(waiting[0].can_cancel,true);result.waitingExecution=waiting[0].execution_id;
  const beforeCancel=snapshot();writeFileSync(root+'/gui-before-cancel.json',JSON.stringify(beforeCancel,null,2));
  assert.equal(beforeCancel.rows.distillation_execution_checkpoints[0][0],result.waitingExecution);
  await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'创建备份',exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'创建备份',exact:true}).isDisabled(),true);
  await shot('04-backup-blocked');
  await page.goto(saved);await page.getByRole('button',{name:'取消本次提炼',exact:true}).click();
  await page.getByText('本次提炼已取消，没有生成洞察。原 Content、字幕、摘要和 Evidence 均保留。',{exact:true}).waitFor();
  await shot('05-cancelled');
  const cancelled=snapshot();
  for(const table of Object.keys(beforeCancel.rows))if(table!=='distillation_waiting_model_cancellations')assert.deepEqual(cancelled.rows[table],beforeCancel.rows[table],table);
  assert.deepEqual(cancelled.files,beforeCancel.files);assert.equal(cancelled.rows.distillation_waiting_model_cancellations.length,1);
  await page.reload();await page.getByText('本次提炼已取消，没有生成洞察。原 Content、字幕、摘要和 Evidence 均保留。',{exact:true}).waitFor();
  await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'创建备份',exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'创建备份',exact:true}).isEnabled(),true);await shot('06-backup-ready');
  await page.getByRole('button',{name:'创建备份',exact:true}).click();await page.getByRole('link',{name:'保存备份文件',exact:true}).waitFor();await shot('07-backup-created');
  const downloadPromise=page.waitForEvent('download');await page.getByRole('link',{name:'保存备份文件',exact:true}).click();
  const download=await downloadPromise,archive=runtimeRoot+'/cancelled-backup.zip';await download.saveAs(archive);
  writeFileSync(root+'/gui-backup-state.json',JSON.stringify(cancelled,null,2));
  await page.getByRole('button',{name:'编辑语言',exact:true}).click();await page.getByLabel('默认输出语言',{exact:true}).selectOption('en');await page.getByRole('button',{name:'保存语言',exact:true}).click();
  assert.notDeepEqual(snapshot().rows.global_user_settings,cancelled.rows.global_user_settings);
  await page.getByLabel('选择备份文件',{exact:true}).setInputFiles(archive);
  await page.getByRole('button',{name:'恢复此备份…',exact:true}).waitFor();await shot('08-restore-preview');
  await page.getByRole('button',{name:'恢复此备份…',exact:true}).click();await page.getByLabel('输入 RESTORE 以确认',{exact:true}).fill('RESTORE');await shot('09-restore-confirm');
  await page.getByRole('button',{name:'确认恢复并重启',exact:true}).click();
  for(let i=0;i<100;i++){
    await page.waitForTimeout(300);
    try{const state=(await (await page.request.get(base+'api/v1/backup-restore/status')).json()).status;if(state.last_restore?.state==='APPLIED'){result.restore=state;break}}catch{}
  }
  assert.equal(result.restore?.last_restore?.state,'APPLIED');
  const restored=snapshot();writeFileSync(root+'/gui-restored-state.json',JSON.stringify(restored,null,2));assert.deepEqual(restored,cancelled);
  await page.goto(saved);await page.getByText('本次提炼已取消，没有生成洞察。原 Content、字幕、摘要和 Evidence 均保留。',{exact:true}).waitFor();await shot('10-restored-cancelled');
  execFileSync('/usr/sbin/screencapture',['-x',root+'/screenshots/11-macos-restored.png']);
  const detail=await (await page.request.get(base+'api/v1/videos/'+contentId)).json();assert.equal(detail.intelligence_result.status,'CANCELLED');assert.deepEqual(detail.waiting_model_executions,[]);
  assert.equal(result.restore.ready,true);assert.deepEqual(errors,[]);
  assert.ok(posts.every(p=>!p.url.includes('/cloud-intelligence/confirm')));
  assert.ok(posts.filter(p=>p.url.includes('/local/native/')).every(p=>p.body==='{}'));
  result.passed=true;result.zeroFileHttpUpload=posts.every(p=>!p.url.includes('/local/imports'));result.preservedAllTablesAndArtifacts=true;result.restartRestore=true;
}catch(e){result.failure=String(e);await shot('failure');throw e}
finally{writeFileSync(root+'/gui-result.json',JSON.stringify({result,errors,posts},null,2)+'\n');await context.close()}
