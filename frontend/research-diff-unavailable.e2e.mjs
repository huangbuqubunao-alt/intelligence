import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import { chromium } from "playwright-core";
const root = new URL("../.var/phase6/corrupt-browser/", import.meta.url);
const info = JSON.parse(readFileSync(new URL("diff-fixture.json", root)));
const base = "http://127.0.0.1:5423/";
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const scenarios = [], pageErrors = [], external = [], expectedResourceErrors = [];
try {
 for (const language of ["zh-CN", "en"]) for (const side of ["base", "target"]) {
  const page = await browser.newPage({viewport:{width:320,height:1000}});
  page.on("pageerror", e=>pageErrors.push(String(e)));
  page.on("console", m=>{if(["error","warning"].includes(m.type())) expectedResourceErrors.push(m.text());});
  page.on("request", r=>{if(!r.url().startsWith(base)) external.push(r.url());});
  await page.addInitScript(l=>localStorage.setItem("yia.ui-language",l),language);
  const a=side==="base"?info.base:info.target,b=side==="base"?info.target:info.base;
  const response=page.waitForResponse(r=>r.url().includes("/diff?")&&r.status()===409);
  await page.goto(`${base}#Research/${info.research_id}/diff/${a}/${b}`);
  assert.equal((await (await response).json()).error.code,"RESEARCH_DIFF_UNTRUSTED_REVISION");
  const alert=await page.getByRole("alert").innerText();
  assert.ok(alert.includes(language==="en"?"failed authority checks":"未通过来源权威核验"));
  assert.equal(await page.locator(".research-diff blockquote").count(),0);
  assert.doesNotMatch(await page.locator(".research-diff").innerText(),/Fixture canonical evidence|RESEARCH_DIFF_|Research could not be read/);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.screenshot({path:new URL(`${language}-${side}-rejected.png`,root).pathname,fullPage:true});
  scenarios.push(`${language}: corrupt ${side} rejected without packet`);await page.close();
 }
 assert.deepEqual(pageErrors,[]);assert.deepEqual(external,[]);
 assert.ok(expectedResourceErrors.length>=4);
 assert.ok(expectedResourceErrors.every(e=>e.includes("409 (Conflict)")),JSON.stringify(expectedResourceErrors));
 writeFileSync(new URL("unavailable-report.json",root),JSON.stringify({scenarios,pageErrors,external,expectedResourceErrors},null,2));
 console.log("4 real corrupt-revision browser rejections passed; deliberate 409 resource errors only, zero JS errors/external requests/overflow/content leakage.");
} finally {await browser.close();}
