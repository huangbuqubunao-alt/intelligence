// Persistent-browser driver for the OpenCode user-pilot session.
// Uses a dedicated Chrome profile so the user's normal Chrome data is untouched.
// Usage: node drive.mjs <command> [json-args]
import { chromium } from "/Users/hua/Documents/yia-worktrees/opencode-user-pilot/frontend/node_modules/playwright-core/index.mjs";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
export const PROFILE = "/Users/hua/Documents/yia-worktrees/opencode-user-pilot/.var/user-pilot/browser-profile";
export const SHOTS = "/Users/hua/Documents/yia-worktrees/opencode-user-pilot/docs/dogfood/opencode-user-pilot/screenshots";
export const BASE = "http://127.0.0.1:5588/";

mkdirSync(PROFILE, { recursive: true });
mkdirSync(SHOTS, { recursive: true });

export async function open({ width = 1440, height = 960, language = null } = {}) {
  const context = await chromium.launchPersistentContext(PROFILE, {
    executablePath: CHROME,
    headless: true,
    viewport: { width, height },
    args: ["--no-first-run", "--no-default-browser-check", "--hide-crash-restore-bubble"],
  });
  const page = context.pages()[0] ?? (await context.newPage());
  if (language) {
    await page.addInitScript((lang) => localStorage.setItem("yia.ui-language", lang), language);
  }
  const errors = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(`console: ${m.text()}`);
  });
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("response", (r) => {
    if (r.status() >= 400) errors.push(`http ${r.status()} ${r.request().method()} ${r.url()}`);
  });
  return { context, page, errors };
}

export async function shot(page, name) {
  const path = `${SHOTS}/${name}.png`;
  await page.screenshot({ path, fullPage: false });
  console.log(`SHOT ${path}`);
  return path;
}