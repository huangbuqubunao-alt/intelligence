import assert from 'node:assert/strict';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from 'playwright-core';

const base = 'http://127.0.0.1:5613/';
const root = process.env.YIA_PHASE11_ROOT ?? new URL('../.var/phase11/browser-fixture/', import.meta.url).pathname;
const info = JSON.parse(readFileSync(join(root, 'fixture.json')));
const offline = process.env.YIA_PHASE11_OFFLINE === '1';
const screenshots = join(root, 'screenshots'); mkdirSync(screenshots, { recursive: true });
const evidence = new URL('../docs/validation/phase11/', import.meta.url).pathname;
mkdirSync(evidence, { recursive: true });
const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true,
  args: ['--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows'] });
const errors = [], external = [], scenarios = [];
const escape = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
let index = 0;
try {
  for (const language of ['zh-CN', 'en']) for (const width of [320, 768, 1024, 1440]) {
    const mid = String(1000 + index++), [old, caption, captionless] = info.creators[mid];
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    page.setDefaultTimeout(30000);
    page.on('pageerror', error => errors.push(String(error)));
    page.on('console', message => { if (['error', 'warning'].includes(message.type())) errors.push(message.text()); });
    page.on('request', request => { if (!request.url().startsWith(base)) external.push(request.url()); });
    page.on('dialog', async dialog => { errors.push('Remote text executed'); await dialog.dismiss(); });
    await page.addInitScript(lang => localStorage.setItem('yia.ui-language', lang), language);
    const text = (en, zh) => language === 'en' ? en : zh;
    const get = async path => { const response = await page.request.get(`${base}api/v1/${path}`); assert.equal(response.status(), 200); return response.json(); };
    const advance = async publish => { const response = await page.request.post(`${base}api/v1/fixture/advance`, { headers: { Origin: base.slice(0, -1), 'X-YIA-Request': 'local-ui' }, data: { mid, publish } }); assert.equal(response.status(), 200); };
    const noOverflow = async () => assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${language}/${width} overflow`);
    const following = async () => { await page.getByRole('navigation').getByRole('button', { name: text('Following', '关注'), exact: true }).click(); };
    const add = async bvid => {
      await following();
      await page.getByRole('button', { name: text('Add Source', '添加关注'), exact: true }).first().click();
      await page.getByRole('button', { name: text('Bilibili', '哔哩哔哩'), exact: true }).click();
      const dialog = page.getByRole('dialog');
      await dialog.getByLabel(text('Bilibili video URL or BV id', '哔哩哔哩视频链接或 BV 号')).fill(bvid);
      await dialog.getByRole('button', { name: text('Import public video', '导入公开视频'), exact: true }).click();
      await dialog.getByRole('link', { name: text('Open Content', '打开内容'), exact: true }).click();
    };
    const detail = async () => {
      await following();
      await page.getByText('公开 UP 主 ' + mid, { exact: true }).first().click();
      const dialog = page.getByRole('dialog', { name: text('Creator Following', 'UP 主关注') });
      await dialog.getByRole('button', { name: text('Check Now', '立即检查'), exact: true }).waitFor();
      return dialog;
    };
    await page.goto(base + '#Home'); await page.locator('.knowledge-delta').waitFor();
    assert.equal(await page.locator('.sidebar-nav button').count(), 6);
    if (!offline) {
      await add(old); await page.locator('.timed-transcript li').first().waitFor();
      await following();
      await page.getByRole('button', { name: text('Add Source', '添加关注'), exact: true }).first().click();
      await page.getByRole('button', { name: text('Bilibili', '哔哩哔哩'), exact: true }).click();
      let dialog = page.getByRole('dialog');
      await dialog.getByRole('button', { name: text('Follow a creator', '关注一个 UP 主'), exact: true }).click();
      await dialog.getByLabel(text('Creator profile URL or numeric id', 'UP 主主页链接或数字 ID')).fill(`https://space.bilibili.com/${mid}/video`);
      await dialog.getByRole('button', { name: text('Follow creator', '关注 UP 主'), exact: true }).click();
      await dialog.getByRole('button', { name: text('Done', '完成'), exact: true }).click();
      assert.equal((await get(`sources/bilibili-creator-${mid}`)).source.tracking.update_count, 0);
      await page.goto(base + '#Content/bilibili-' + old);
      await page.getByRole('button', { name: text('Follow this creator', '关注此 UP 主'), exact: true }).click();
      await page.getByRole('status').getByText(text('Creator followed. Check the Following detail for its starting point and source health.', '已关注 UP 主，请在关注详情中查看跟踪起点和来源状态。'), { exact: true }).waitFor();
      assert.equal((await get('sources')).sources.filter(source => source.source_id === `bilibili-creator-${mid}`).length, 1);
      dialog = await detail();
      assert.ok((await dialog.innerText()).includes(text('No new public videos have been discovered yet.', '尚未发现新的公开视频。')));
      await dialog.getByRole('button', { name: text('Check Now', '立即检查'), exact: true }).click();
      await noOverflow();
      await page.screenshot({ path: join(screenshots, `${language}-${width}-baseline.png`), fullPage: true });
      await dialog.getByRole('button', { name: text('Close', '关闭'), exact: true }).click();
      await advance(true);
      await add(caption); // Manually imported Content must be reused by discovery.
      dialog = await detail();
      await dialog.getByRole('button', { name: text('Check Now', '立即检查'), exact: true }).click();
      await page.waitForFunction(async id => {
        const result = await (await fetch(`/api/v1/sources/${id}`)).json();
        return result.source.tracking.update_count === 2 && !result.source.tracking.checking;
      }, `bilibili-creator-${mid}`);
      await dialog.getByRole('link', { name: new RegExp(escape(captionless)) }).waitFor();
      await noOverflow();
      await page.screenshot({ path: join(screenshots, `${language}-${width}-updates.png`), fullPage: true });
      await dialog.getByRole('button', { name: text('Pause monitoring', '暂停监测'), exact: true }).click();
      await dialog.getByRole('button', { name: text('Resume monitoring', '继续关注'), exact: true }).waitFor();
      assert.equal((await get(`sources/bilibili-creator-${mid}`)).source.enabled, false);
      await dialog.getByRole('button', { name: text('Resume monitoring', '继续关注'), exact: true }).click();
      await dialog.getByRole('button', { name: text('Pause monitoring', '暂停监测'), exact: true }).waitFor();
      await advance(false);
      await dialog.getByRole('button', { name: text('Check Now', '立即检查'), exact: true }).click();
      await page.waitForFunction(async id => !(await (await fetch(`/api/v1/sources/${id}`)).json()).source.tracking.checking, `bilibili-creator-${mid}`);
      await dialog.getByRole('button', { name: text('Close', '关闭'), exact: true }).click();
      // A discovered Content's technical per-video source is not another Following.
      for (const bv of [caption, captionless]) assert.equal(await page.locator('.source-row').getByText(new RegExp(escape(bv))).count(), 0);
    } else {
      const before = (await get(`sources/bilibili-creator-${mid}`)).source;
      await advance(false);
      const dialog = await detail();
      await dialog.getByRole('button', { name: text('Check Now', '立即检查'), exact: true }).click();
      await page.waitForFunction(async id => (await (await fetch(`/api/v1/sources/${id}`)).json()).source.tracking.health === 'OFFLINE', `bilibili-creator-${mid}`);
      const after = (await get(`sources/bilibili-creator-${mid}`)).source;
      assert.equal(after.last_success_at, before.last_success_at);
      assert.equal(after.tracking.verified_at, before.tracking.verified_at);
      assert.equal(after.tracking.update_count, 2);
      await dialog.getByText(text('Unable to connect. Your last successful check is preserved.', '暂时无法连接，已保留上次成功检查的状态。'), { exact: true }).waitFor();
      await noOverflow(); await page.screenshot({ path: join(screenshots, `offline-${language}-${width}-source.png`), fullPage: true });
      await dialog.getByRole('button', { name: text('Close', '关闭'), exact: true }).click();
    }
    await page.goto(base + '#Content/bilibili-' + captionless);
    await page.getByRole('button', { name: text('Retry public captions', '重试获取公开字幕'), exact: true }).waitFor();
    assert.ok((await page.locator('body').innerText()).includes(text('Summary and Evidence require trusted captions', '摘要和证据需要可信字幕')));
    assert.equal(await page.locator('.timed-transcript').count(), 0);
    await noOverflow();
    await page.goto(base + '#Content/bilibili-' + caption);
    await page.locator('.timed-transcript li').first().waitFor();
    await page.locator('[id^="content-evidence-"]').first().waitFor();
    assert.ok((await page.locator('body').innerText()).includes('Sentence1 公开字幕支持可信的来源证据。'));
    assert.equal(await page.getByRole('button', { name: text('Transcribe on device', '在设备上转写'), exact: true }).count(), 0);
    await noOverflow(); await page.screenshot({ path: join(screenshots, `${offline ? 'offline-' : ''}${language}-${width}-content.png`), fullPage: true });
    await page.reload(); await page.locator('.timed-transcript li').first().waitFor();
    const contents = (await get('videos')).videos;
    assert.deepEqual([...new Set(contents.map(content => content.provider))].sort(), ['BILIBILI', 'LOCAL', 'YOUTUBE']);
    for (const bv of [old, caption, captionless]) assert.equal(contents.filter(content => content.video_id === 'bilibili-' + bv).length, 1);
    await page.getByRole('navigation').getByRole('button', { name: text('Intelligence', '洞察'), exact: true }).click();
    await page.getByRole('button', { name: text('Research', '研究'), exact: true }).click();
    await page.getByRole('button', { name: text('New Research', '新建研究'), exact: true }).click();
    await page.getByLabel(text('Research question', '研究问题')).fill('sentence1 four content public evidence');
    for (const id of [info.youtube_id, info.local_id, 'bilibili-' + old, 'bilibili-' + caption]) {
      await page.getByRole('checkbox', { name: new RegExp(escape(contents.find(content => content.video_id === id).title)) }).check();
    }
    await page.getByRole('button', { name: text('Assemble library packet', '收集资料库证据包'), exact: true }).click();
    await page.locator('.research-result blockquote').first().waitFor();
    const research = await page.locator('.research-result').innerText();
    for (const label of ['YouTube', text('Local', '本地'), text('Bilibili', '哔哩哔哩')]) assert.ok(research.includes(label));
    await noOverflow(); await page.screenshot({ path: join(screenshots, `${offline ? 'offline-' : ''}${language}-${width}-research.png`), fullPage: true });
    await page.getByRole('navigation').getByRole('button', { name: text('Home', '首页'), exact: true }).click();
    await page.locator('.knowledge-delta').waitFor(); await noOverflow();
    await page.getByRole('navigation').getByRole('button', { name: text('Settings', '设置'), exact: true }).click();
    await page.getByText(text('Deep Analysis is unavailable.', '深度分析不可用。'), { exact: true }).first().waitFor();
    await noOverflow();
    scenarios.push({ language, width, offline, mid, flows: 'manual import; creator baseline; follow from Content; cooldown; discovery/dedupe; no-op; pause/resume; captions/no-captions; restart; Research; Delta; Settings' });
    await page.close();
  }
  if (!offline) {
    const page = await browser.newPage({ viewport: { width: 320, height: 1000 } });
    page.setDefaultTimeout(30000);
    page.on('pageerror', error => errors.push(String(error)));
    page.on('console', message => { if (['error', 'warning'].includes(message.type())) errors.push(message.text()); });
    page.on('request', request => { if (!request.url().startsWith(base)) external.push(request.url()); });
    await page.addInitScript(() => localStorage.setItem('yia.ui-language', 'en'));
    await page.goto(base + '#Following');
    await page.getByRole('button', { name: 'Add Source', exact: true }).first().click();
    await page.getByRole('button', { name: 'Bilibili', exact: true }).click();
    let dialog = page.getByRole('dialog');
    await dialog.getByRole('button', { name: 'Follow a creator', exact: true }).click();
    await dialog.getByLabel('Creator profile URL or numeric id').fill('1008');
    await dialog.getByRole('button', { name: 'Follow creator', exact: true }).click();
    await dialog.getByRole('button', { name: 'Done', exact: true }).click();
    const advance = await page.request.post(`${base}api/v1/fixture/advance`, { headers: { 'X-YIA-Request': 'local-ui' }, data: { mid: '1008', publish: true } });
    assert.equal(advance.status(), 200);
    await page.reload(); // Opening Following checks a stale source without Check Now.
    await page.waitForFunction(async () => {
      const body = await (await fetch('/api/v1/sources/bilibili-creator-1008')).json();
      return body.source.tracking.update_count === 2 && !body.source.tracking.checking;
    });
    await page.getByLabel('Following filter').selectOption('updates');
    await page.getByText('公开 UP 主 1008', { exact: true }).waitFor();
    for (const bv of info.creators['1008'].slice(1)) assert.equal(await page.locator('.source-row').getByText(new RegExp(escape(bv))).count(), 0);
    await page.getByText('公开 UP 主 1008', { exact: true }).click();
    dialog = page.getByRole('dialog', { name: 'Creator Following' });
    await dialog.locator('li').first().waitFor();
    assert.equal(await dialog.locator('li').count(), 2);
    await page.screenshot({ path: join(screenshots, 'en-320-stale-source-automatic.png'), fullPage: true });
    scenarios.push({ language: 'en', width: 320, mid: '1008', flows: 'numeric creator input; automatic stale-source discovery; live list refresh; Has updates; grouped Following without per-video rows' });
    await page.close();
  }
  assert.deepEqual(errors, []); assert.deepEqual(external, []);
  writeFileSync(join(evidence, offline ? 'creator-offline-browser.json' : 'creator-browser.json'), JSON.stringify({ fixture: true, scenarios, errors, external, overflow: 0, noNewPrimaryNavigation: true }, null, 2));
  console.log(`${scenarios.length} creator Following HTTP/SQLite/worker browser flows passed.`);
} catch (error) {
  for (const [index, page] of browser.contexts().flatMap(context => context.pages()).entries()) {
    writeFileSync(join(evidence, `browser-failure-${index}.json`), JSON.stringify({ url: page.url(), text: await page.locator('body').innerText(), errors, external }, null, 2));
    await page.screenshot({ path: join(screenshots, `failure-${index}.png`), fullPage: true });
  }
  throw error;
} finally { await browser.close(); }
