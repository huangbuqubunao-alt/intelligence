import { open, shot, BASE } from "./browser.mjs";

const { context, page, errors } = await open({ width: 1440, height: 960 });

console.log("=== navigating to fresh product ===");
await page.goto(BASE, { waitUntil: "networkidle" });
await page.waitForTimeout(1200);

console.log("URL:", page.url());
console.log("TITLE:", await page.title());

const text = await page.evaluate(() => document.body.innerText);
console.log("--- VISIBLE TEXT (first 3000 chars) ---");
console.log(text.slice(0, 3000));

console.log("--- HEADINGS ---");
console.log(
  JSON.stringify(
    await page.evaluate(() =>
      [...document.querySelectorAll("h1,h2,h3,h4")].map((e) => `${e.tagName}: ${e.innerText}`),
    ),
    null,
    1,
  ),
);

console.log("--- BUTTONS / LINKS ---");
console.log(
  JSON.stringify(
    await page.evaluate(() =>
      [...document.querySelectorAll("button,a[href],[role=button]")].map((e) => ({
        tag: e.tagName,
        text: (e.innerText || e.getAttribute("aria-label") || "").trim().slice(0, 60),
        disabled: e.disabled === true || e.getAttribute("aria-disabled") === "true",
        href: e.getAttribute("href"),
      })),
    ),
    null,
    1,
  ),
);

await shot(page, "01-first-open");
console.log("--- ERRORS ---");
console.log(errors.length ? errors.join("\n") : "(none)");
await context.close();