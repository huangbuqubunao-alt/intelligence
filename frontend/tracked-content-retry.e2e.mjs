import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import { chromium } from 'playwright-core';

const base = process.env.YIA_BROWSER_BASE ?? 'http://127.0.0.1:5840/';
const output = new URL('../docs/validation/end-to-end-user-readiness/tracked-retry-browser/', import.meta.url);
mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const errors = [], external = [], requests = [], snapshots = [];
const pages = [];
try {
  for (const language of ['en', 'zh-CN']) for (const width of [1440, 320]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    page.on('pageerror', error => errors.push(String(error)));
    page.on('console', event => { if (['error', 'warning'].includes(event.type())) errors.push(event.text()); });
    page.on('request', request => {
      if (!request.url().startsWith(base)) external.push(request.url());
      if (request.method() === 'POST' && request.url().includes('/content/')) requests.push({ url: request.url(), body: request.postDataJSON() });
    });
    await page.addInitScript(value => localStorage.setItem('yia.ui-language', value), language);
    pages.push({ page, language, width });
  }
  const leader = pages[0].page;
  async function capture(state) {
    const stateText = {
      ELIGIBLE: /Retry native captions for this followed Content|为此关注内容重试原生字幕/,
      QUEUED: /Caption retry is queued|字幕重试已排队/,
      CANCELLED: /Caption retry was cancelled before reading began|已在开始读取前取消字幕重试/,
      ATTENTION: /Captions are saved, but local organization needs attention|字幕已保存，但本地整理需要处理/,
      FINALIZING: /Captions are saved. Preparing source references|字幕已保存，正在本地整理/,
      SUCCEEDED: /Captions, source references and Summary are ready|字幕、来源引用与摘要已就绪/,
    };
    for (const { page, language, width } of pages) {
      await page.goto(base + '?capture=' + state + '#Content/newvideo001');
      const region = page.getByRole('region', { name: language === 'en' ? 'Caption retry' : '字幕重试' });
      await region.waitFor();
      await region.getByText(stateText[state]).waitFor();
      await region.scrollIntoViewIfNeeded();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      const response = await page.request.get(base + 'api/v1/content/newvideo001/retry');
      const status = (await response.json()).tracked_content_retry;
      assert.equal(status.request?.state ?? 'ELIGIBLE', state);
      await page.screenshot({ path: new URL(`${language}-${width}-${state}.png`, output).pathname, fullPage: true });
      snapshots.push({ language, width, state, text: await region.innerText(), overflow: false });
    }
  }
  const action = async path => {
    const result = await leader.request.post(base + 'api/v1/fixture/' + path, { headers: { 'X-YIA-Request': 'local-ui' }, data: {} });
    assert.equal(result.status(), 200);
    return result.json();
  };
  const clickAction = async name => {
    const response = leader.waitForResponse(result => result.request().method() === 'POST' && result.url().includes('/content/newvideo001/retry'));
    await leader.getByRole('button', { name, exact: true }).click();
    const result = await response;
    assert.equal(result.status(), 202, await result.text());
    return result.json();
  };
  await capture('ELIGIBLE');
  await clickAction('Retry captions');
  await leader.getByRole('button', { name: 'Cancel caption retry', exact: true }).waitFor();
  await capture('QUEUED');
  await clickAction('Cancel caption retry');
  await leader.getByText('Caption retry was cancelled before reading began.', { exact: true }).waitFor();
  await capture('CANCELLED');
  await clickAction('Retry captions');
  await leader.getByRole('button', { name: 'Cancel caption retry', exact: true }).waitFor();
  const acquired = await action('run');
  assert.deepEqual(acquired.calls, ['enumerate_tracks', 'read_track']);
  await capture('ATTENTION');
  await action('local-ready');
  await clickAction('Retry local organization');
  await capture('FINALIZING');
  assert.deepEqual((await action('run')).calls, acquired.calls);
  await capture('SUCCEEDED');
  const proof = await (await leader.request.get(base + 'api/v1/fixture/proof')).json();
  assert.equal(proof.attempts.length, 2);
  assert.deepEqual(proof.attempts.map(row => row.attempt_count).sort(), [0, 1]);
  assert.equal(proof.attempts.filter(row => row.status === 'SUCCEEDED').length, 1);
  const evidence = await (await leader.request.get(base + 'api/v1/videos/newvideo001/evidence')).json();
  assert.ok(evidence.evidence.length > 0);
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  writeFileSync(new URL('result.json', output), JSON.stringify({ snapshots, requests, proof, evidence_count: evidence.evidence.length, errors, external }, null, 2) + '\n');
  console.log('24 real Chrome bilingual narrow/wide states; cancel → new command → local attention → resume → Summary/Evidence passed');
} finally {
  await browser.close();
}
