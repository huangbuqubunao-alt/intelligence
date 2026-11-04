// This scope verifies settings and populated restore, not models or all user journeys.
import { createHash } from 'node:crypto';
import { mkdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const output = join(root, '.var', 'gui-e2e', `${Date.now()}-${process.pid}`);
mkdirSync(output, { recursive: true });
const required = ['qaGuard', 'uiOpened', 'languageRoundTrip', 'unsavedDraftCleared', 'backupCreated', 'restoreApplied', 'populatedViewsUnchanged', 'topicsOpened'];
const result = {
  scope: 'GUI_SETTINGS_AND_POPULATED_RESTORE', success: false, mode: 'HEADED', steps: {}, errors: [],
  nativeMacOSAcceptance: 'NOT_PERFORMED', modelQuality: 'NOT_PERFORMED',
  exactSchemaVerification: 'NOT_PERFORMED_BACKEND_CHECKS_SEPARATE',
  onboarding: 'NOT_PERFORMED_POPULATED_FIXTURE_SCOPE', restoreObservations: [], archiveSchemaVersion: null,
};
class Failure extends Error { constructor(code) { super(code); this.code = code; } }
const require = (ok, code) => { if (!ok) throw new Failure(code); };
const save = (name, value) => writeFileSync(join(output, name), JSON.stringify(value, null, 2) + '\n');
const hash = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
let step = 'arguments', browser, context, page, restarting = false, observing = true;
let base, api, timeout = 15000, restoreTimeout = 60000;
const diagnostics = new Set();
function loopback(value) {
  const u = new URL(value);
  require(u.protocol === 'http:' && ['127.0.0.1', '[::1]'].includes(u.hostname) && Number(u.port) >= 1024
    && !u.username && !u.password && u.pathname === '/' && !u.search && !u.hash, 'LOOPBACK_TARGET_REQUIRED');
  return u.origin;
}
function argumentsForRun() {
  const args = process.argv.slice(2);
  let front = 'http://127.0.0.1:6379/', back = 'http://127.0.0.1:6378/';
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--headless') result.mode = 'HEADLESS';
    else if (args[i] === '--headed') result.mode = 'HEADED';
    else if (args[i] === '--base-url') front = args[++i];
    else if (args[i] === '--api-url') back = args[++i];
    else if (args[i] === '--timeout-ms') timeout = Number(args[++i]);
    else if (args[i] === '--restore-timeout-ms') restoreTimeout = Number(args[++i]);
    else throw new Failure('UNKNOWN_ARGUMENT');
  }
  base = loopback(front); api = loopback(back);
  require(Number.isInteger(timeout) && timeout >= 1000 && timeout <= 60000, 'INVALID_STEP_TIMEOUT');
  require(Number.isInteger(restoreTimeout) && restoreTimeout >= 1000 && restoreTimeout <= 90000, 'INVALID_RESTORE_TIMEOUT');
}
async function json(origin, path) {
  const response = await fetch(origin + path, { redirect: 'error', signal: AbortSignal.timeout(Math.min(timeout, 5000)) });
  require(response.ok, `HTTP_${response.status}`); return response.json();
}
const unavailable = e => e instanceof TypeError && ['ECONNREFUSED', 'ECONNRESET', 'UND_ERR_SOCKET'].includes(e.cause?.code);
const reconnectPath = path => ['/api/v1/backup-restore/status', '/api/v1/settings'].includes(path);
async function proxyReconnect(url, method, status) {
  if (!(restarting && method === 'GET' && reconnectPath(new URL(url).pathname) && [500, 502, 503].includes(status))) return false;
  try { await json(api, '/api/v1/backup-restore/status'); }
  catch (e) { if (unavailable(e)) { result.restoreObservations.push('PROXY_RECONNECT_WHILE_API_UNAVAILABLE'); return true; } }
  return false;
}
function diagnostic(work) {
  const task = work().catch(() => result.errors.push('DIAGNOSTIC_CHECK_FAILED'));
  diagnostics.add(task); task.finally(() => diagnostics.delete(task));
}
async function checked(name, work) {
  step = name; await work();
  if (page && !page.isClosed()) await page.waitForLoadState('networkidle', { timeout });
  await Promise.all([...diagnostics]);
  require(result.errors.length === 0, 'BROWSER_ERROR'); result.steps[name] = 'PASS'; save('result.json', result);
}
async function qaGuard() {
  for (const origin of new Set([base, api])) require((await json(origin, '/api/v1/settings')).cloud_execution_enabled === false, 'QA_SPENDING_GUARD_REQUIRED');
}
async function snapshot() {
  const { videos } = await json(base, '/api/v1/videos');
  require(Array.isArray(videos) && videos.length > 0, 'POPULATED_CONTENT_FIXTURE_REQUIRED');
  const content = [], evidence = [];
  for (const v of videos) {
    require(typeof v.video_id === 'string' && v.video_id.length > 0, 'CONTENT_ID_REQUIRED');
    content.push({ id: v.video_id, hash: hash([v.provider, v.title, v.source_url, v.pipeline_status]) });
    const view = await json(base, `/api/v1/videos/${encodeURIComponent(v.video_id)}/evidence`);
    require(Array.isArray(view.evidence), 'EVIDENCE_VIEW_REQUIRED');
    for (const e of view.evidence) {
      require(typeof e.evidence_id === 'string' && typeof e.original_excerpt === 'string' && e.original_excerpt.length > 0, 'TRUSTED_EVIDENCE_ID_AND_TEXT_REQUIRED');
      evidence.push({ content: v.video_id, id: e.evidence_id, hash: hash(e) });
    }
  }
  require(evidence.length > 0, 'POPULATED_EVIDENCE_FIXTURE_REQUIRED');
  content.sort((a, b) => a.id.localeCompare(b.id)); evidence.sort((a, b) => a.id.localeCompare(b.id));
  return { content, evidence }; // Do not persist raw source text.
}
async function waitApplied(id) {
  const deadline = Date.now() + restoreTimeout;
  while (Date.now() < deadline) {
    try {
      const { status } = await json(api, '/api/v1/backup-restore/status');
      if (status.restore_pending) result.restoreObservations.push('PENDING');
      if (status.last_restore?.restore_id === id) {
        require(status.last_restore.state === 'APPLIED', 'RESTORE_REJECTED_OR_ROLLED_BACK');
        require(status.restore_pending === false && Number.isFinite(Date.parse(status.last_restore.completed_at)), 'RESTORE_RECEIPT_INCOMPLETE');
        result.restoreObservations.push('APPLIED'); return;
      }
    } catch (e) { if (!unavailable(e)) throw e; result.restoreObservations.push('API_RECONNECTING'); }
    await pause(200);
  }
  throw new Failure('RESTORE_APPLIED_TIMEOUT');
}
try {
  argumentsForRun(); await checked('qaGuard', qaGuard);
  step = 'populatedFixture'; await snapshot(); // Fresh onboarding is a separate scope, never silently marked passed.
  step = 'browserLaunch';
  const { chromium } = await import('../frontend/node_modules/playwright-core/index.mjs');
  browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: result.mode === 'HEADLESS', args: ['--no-first-run', '--no-default-browser-check'] });
  context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
  await context.route('**/*', async route => {
    const r = route.request(), u = new URL(r.url()), m = r.method();
    const permitted = (m === 'PUT' && u.pathname === '/api/v1/settings/output-language') || (m === 'POST' && ['/api/v1/backup-restore/backups', '/api/v1/backup-restore/restore/stage', '/api/v1/backup-restore/restore/confirm'].includes(u.pathname));
    if (![base, api].includes(u.origin) || (!['GET', 'HEAD', 'OPTIONS'].includes(m) && !permitted)) { result.errors.push('OUT_OF_SCOPE_NETWORK_OR_MUTATION_BLOCKED'); await route.abort(); }
    else await route.continue();
  });
  page = await context.newPage(); page.setDefaultTimeout(timeout);
  page.on('pageerror', () => { if (observing) result.errors.push('PAGE_ERROR'); });
  page.on('response', r => { if (observing && r.status() >= 400) diagnostic(async () => { if (!await proxyReconnect(r.url(), r.request().method(), r.status())) result.errors.push(`HTTP_${r.status()}`); }); });
  page.on('requestfailed', r => {
    if (!observing) return;
    const transient = restarting && r.method() === 'GET' && reconnectPath(new URL(r.url()).pathname) && /ERR_CONNECTION_REFUSED|ERR_CONNECTION_RESET|ERR_EMPTY_RESPONSE|ERR_CONNECTION_CLOSED/.test(r.failure()?.errorText ?? '');
    if (transient) result.restoreObservations.push('BROWSER_RECONNECTING'); else result.errors.push('REQUEST_FAILED');
  });
  page.on('console', m => {
    if (observing && m.type() === 'error') diagnostic(async () => {
      const location = m.location().url, status = /status of (500|502|503)/.exec(m.text());
      if (!(location && status && await proxyReconnect(location, 'GET', Number(status[1])))) result.errors.push('CONSOLE_ERROR');
    });
  });
  await checked('uiOpened', async () => { await page.goto(base, { waitUntil: 'domcontentloaded' }); await page.getByRole('button', { name: /^(设置|Settings)$/ }).waitFor(); });
  await page.getByRole('button', { name: /^(设置|Settings)$/ }).click();
  await checked('languageRoundTrip', async () => {
    await page.getByRole('button', { name: /^(编辑语言|Edit language)$/ }).waitFor();
    async function change(zh, target) {
      await page.getByRole('button', { name: zh ? '编辑语言' : 'Edit language', exact: true }).click();
      await page.getByLabel(zh ? '界面语言' : 'Interface language', { exact: true }).selectOption(target);
      await page.getByLabel(zh ? '默认输出语言' : 'Preferred output language', { exact: true }).selectOption(target);
      await page.getByRole('button', { name: zh ? '保存语言' : 'Save language', exact: true }).click();
      await page.getByRole('button', { name: target === 'en' ? 'Edit language' : '编辑语言', exact: true }).waitFor();
      require((await json(base, '/api/v1/settings')).general.output_language === target, 'OUTPUT_LANGUAGE_NOT_PERSISTED');
    }
    if (!await page.getByRole('button', { name: '编辑语言', exact: true }).isVisible()) await change(false, 'zh-CN');
    await change(true, 'en'); await change(false, 'zh-CN');
  });
  await checked('unsavedDraftCleared', async () => {
    await page.locator('summary', { hasText: /云端配置与模型详情|Cloud setup and model details/ }).click();
    const kimi = page.locator('summary', { hasText: /Kimi \/ Moonshot API/ }); await kimi.click();
    const input = page.locator('#moonshot-api-key'); await input.fill('synthetic-unsaved-qa-draft');
    await page.locator('summary', { hasText: /智谱 GLM-4.7-Flash|Zhipu GLM-4.7-Flash/ }).click(); await kimi.click();
    require(await input.inputValue() === '', 'CREDENTIAL_DRAFT_NOT_CLEARED'); await kimi.click();
  });
  const before = await snapshot(); save('before-view-identities.json', before);
  let backupPath;
  await checked('backupCreated', async () => {
    const { status } = await json(api, '/api/v1/backup-restore/status'); require(status.ready === true && status.restore_pending === false, 'BACKUP_NOT_READY');
    const button = page.getByRole('button', { name: /^(创建备份|Create Backup)$/ }); require(await button.isEnabled(), 'BACKUP_BUTTON_DISABLED'); await button.click();
    const link = page.getByRole('link', { name: /保存备份文件|Save backup file/ }); await link.waitFor();
    const pending = page.waitForEvent('download'); pending.catch(() => {});
    await link.click(); const download = await pending;
    require(await download.failure() === null, 'BACKUP_DOWNLOAD_FAILED'); backupPath = join(output, 'candidate-backup.zip'); await download.saveAs(backupPath);
    require(statSync(backupPath).size > 0, 'BACKUP_FILE_MISSING');
  });
  await checked('restoreApplied', async () => {
    const staged = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/backup-restore/restore/stage' && r.request().method() === 'POST');
    staged.catch(() => {}); // still rejects when awaited; avoid an orphan rejection if the preceding UI action fails
    await page.getByLabel(/选择备份文件|Choose backup file/).setInputFiles(backupPath);
    const response = await staged; require(response.ok(), 'RESTORE_STAGE_FAILED'); const { restore } = await response.json();
    require(typeof restore.restore_id === 'string' && /^[a-f0-9]{32}$/.test(restore.restore_id) && restore.preview.content_count > 0 && restore.preview.evidence_count > 0 && restore.preview.data_file_count > 0, 'POPULATED_RESTORE_PREVIEW_REQUIRED');
    result.archiveSchemaVersion = restore.preview.schema_version; // Actual archive version, not exact-schema verification.
    await page.getByRole('button', { name: /恢复此备份|Restore this backup/ }).click(); await page.getByLabel(/输入 RESTORE 以确认|Type RESTORE to confirm/).fill('RESTORE');
    const confirmed = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/backup-restore/restore/confirm' && r.request().method() === 'POST');
    confirmed.catch(() => {});
    restarting = true; await page.getByRole('button', { name: /确认恢复并重启|Confirm Restore and restart/ }).click();
    const confirmation = await confirmed; require(confirmation.ok(), 'RESTORE_CONFIRM_FAILED'); const ack = (await confirmation.json()).restore;
    require(ack.restore_id === restore.restore_id && ack.pending === true && ack.restart_required === true, 'RESTORE_PENDING_ACK_REQUIRED');
    result.restoreObservations.push('CONFIRMED_PENDING_RESTART_REQUIRED'); await waitApplied(restore.restore_id); await qaGuard();
    await page.getByText(/备份已恢复，重启后的数据检查已通过。|Restore completed successfully\./).waitFor(); restarting = false;
  });
  await checked('populatedViewsUnchanged', async () => { const after = await snapshot(); save('after-view-identities.json', after); require(hash(after) === hash(before), 'CONTENT_EVIDENCE_VIEW_CHANGED_AFTER_RESTORE'); });
  await checked('topicsOpened', async () => { await page.getByRole('button', { name: '主题', exact: true }).click(); await page.getByRole('heading', { name: '主题', exact: true }).waitFor(); });
  require(required.every(name => result.steps[name] === 'PASS') && result.errors.length === 0, 'REQUIRED_STEPS_INCOMPLETE'); result.success = true;
} catch (e) {
  result.errors.push(e instanceof Failure ? e.code : e.name === 'TimeoutError' ? 'GUI_TIMEOUT'
    : unavailable(e) ? 'API_CONNECTION_UNAVAILABLE' : e.code === 'ERR_MODULE_NOT_FOUND' ? 'PLAYWRIGHT_NOT_AVAILABLE' : 'GUI_STEP_FAILED');
  result.failedStep = step; process.exitCode = 1; // Do not emit raw exception/DOM/password text.
}
finally {
  observing = false; await Promise.all([...diagnostics]); if (result.errors.length) { result.success = false; process.exitCode = 1; }
  if (page && !page.isClosed()) { try { await page.screenshot({ path: join(output, 'final-masked.png'), mask: [page.locator('input[type="password"]')], timeout }); } catch { result.screenshot = 'UNAVAILABLE'; } }
  try { await context?.close(); await browser?.close(); } catch { result.errors.push('BROWSER_CLOSE_FAILED'); result.success = false; process.exitCode = 1; }
  save('result.json', result); console.log(JSON.stringify({ success: result.success, scope: result.scope, mode: result.mode, result: join(output, 'result.json') }));
}
