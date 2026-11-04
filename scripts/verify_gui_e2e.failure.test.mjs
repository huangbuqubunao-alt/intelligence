// Exercise the real process: a failed check must produce a failed receipt AND exit.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

test('GUI runner rejects unsafe targets, missing QA guard and empty authority without mutations', { timeout: 15000 }, async () => {
  let fixture = 'unguarded', mutations = 0, requests = 0;
  const server = createServer((request, response) => {
    requests++;
    if (request.method !== 'GET') mutations++;
    response.setHeader('Content-Type', 'application/json');
    let payload = {};
    if (request.url === '/api/v1/settings') payload = { cloud_execution_enabled: fixture === 'unguarded' };
    if (request.url === '/api/v1/videos') payload = { videos: fixture === 'no-evidence' ? [{ video_id: 'public-fixture', provider: 'YOUTUBE' }] : [] };
    if (request.url?.endsWith('/evidence')) payload = { evidence: [] };
    response.end(JSON.stringify(payload));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}/`;
  const script = fileURLToPath(new URL('./verify_gui_e2e.mjs', import.meta.url));
  async function rejected(expected, extra = []) {
    const child = spawn(process.execPath, [script, '--base-url', origin, '--api-url', origin, '--headless', '--timeout-ms', '1000', ...extra], { stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '', errors = '';
    child.stdout.on('data', chunk => { output += chunk; });
    child.stderr.on('data', chunk => { errors += chunk; });
    const code = await new Promise((resolve, reject) => { child.once('error', reject); child.once('close', resolve); });
    assert.equal(code, 1, errors);
    const summary = JSON.parse(output.trim());
    assert.equal(summary.success, false);
    const receipt = JSON.parse(readFileSync(summary.result, 'utf8'));
    assert.equal(receipt.success, false);
    assert.ok(receipt.errors.includes(expected), receipt.errors.join(','));
    assert.equal(receipt.mode, 'HEADLESS');
    assert.equal(receipt.nativeMacOSAcceptance, 'NOT_PERFORMED');
    assert.equal(receipt.steps.restoreApplied, undefined);
  }
  try {
    await rejected('QA_SPENDING_GUARD_REQUIRED');
    fixture = 'empty-content';
    await rejected('POPULATED_CONTENT_FIXTURE_REQUIRED');
    fixture = 'no-evidence';
    await rejected('POPULATED_EVIDENCE_FIXTURE_REQUIRED');
    const before = requests;
    await rejected('LOOPBACK_TARGET_REQUIRED', ['--base-url', 'https://example.invalid/']);
    assert.equal(requests, before); // public target rejected before any HTTP request
    assert.equal(mutations, 0);
  } finally {
    await new Promise(resolve => server.close(resolve));
  }
});
