// Diagnose: which hashes render correctly on full page load?
import { open, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });

for (const route of ["#Following", "#Content", "#Intelligence", "#Topics", "#Settings", "#Home"]) {
  await page.goto(BASE + route, { waitUntil: "networkidle" });
  let seen = null;
  for (let i = 0; i < 6; i += 1) {
    await page.waitForTimeout(1000);
    const h1 = await page.evaluate(() => document.querySelector("h1")?.innerText ?? "(no h1)");
    if (h1 && h1 !== seen) { seen = h1; console.log(`  ${route} t+${i + 1}s h1=${h1}`); }
  }
  const snap = await page.evaluate(() => ({
    hash: location.hash,
    h1: document.querySelector("h1")?.innerText ?? "(no h1)",
    bodyStart: document.body.innerText.slice(0, 120).replace(/\n/g, " | "),
  }));
  console.log(`FINAL ${route}: hash=${snap.hash} h1=${snap.h1} body=${snap.bodyStart}`);
}

console.log("--- ERRORS ---");
console.log(errors.length ? errors.join("\n") : "(none)");
await context.close();
