---
name: Intelligence workspace
source: styles.css
---

# Workspace design reference

Reuse the live workspace's dark surfaces, green accent, muted typography, Panel
borders, radius tokens and button styles from styles.css. Do not redesign Home.

One Home section headed “最近 7 天发生了什么变化？” / “What changed in the last
7 days?”. Show the exact localized interval and configured timezone, a compact
five-category count strip, and at most two factual items per category. On wide
screens groups use two columns; on small screens one. Count cells wrap from five
to three to two columns. Long original titles wrap rather than widen the page.

Keep h1 for Home, h2 for this section, h3 for grouped changes. Give the section an
accessible name. Counts are a definition list; items are real lists; navigation
uses keyboard-accessible buttons. Dates are explicit, original titles are context,
recorded validation state is historical, and Evidence membership changes never
imply stronger support. No raw enums, unread badges or personalized mind claims.

Zero changes gets one muted factual sentence. Loading uses role=status. Partial
and unavailable results are visible, localized, retryable and never called empty.
No primary nav item, chart, generated narrative or second feed.

## Research Lite

Preserve the six live primary destinations. Intelligence opens a dedicated
Research view with an explicit question and 1–20 selected library Content items.
Reuse existing Panel, field, button and dark-surface tokens. Question, selected
scope, grouped source Evidence, recorded Intelligence interpretations and
unresolved points are distinct readable sections. Never call this model-generated
research or imply a new conclusion. Show word-matching and bounded-result limits.
Source quotes remain original text, wrap at narrow widths and carry real timing,
language and Content links; raw ids are never primary copy. Existing opinions and
recorded states retain their qualification. Error/loading/empty states are
localized and accessible. Revision comparison follows the Phase 6 section below;
no chat, export or promotion control.


## Research History

Keep History inside Research detail. Reuse existing Panel, metadata rows, source
links and secondary buttons. A current/previous-version heading identifies the
packet; previous packets are explicitly read-only with a return-to-current action.
History is timestamp-first metadata, never raw ids or comparison prose. Show at
most 25 entries with Previous/Next controls; replace the page instead of endlessly
appending rows. The empty previous-version state is legitimate. Excluded invalid
versions and current unavailability are localized factual states, never rendered
payloads or an assertion that all history is empty. Source navigation retains the
opened packet's own references and return route. Preserve keyboard-accessible
buttons, semantic lists, wrapped text and zh-CN/en at 320–1440px. No seventh nav
entry, watermark, unread badge or generated summary is introduced.

## Research revision comparison

Phase 6 extends History with a derived comparison. Preserve the six destinations,
dark Panel surfaces and existing buttons. Current compares with the previous
trusted version on the first History page; opened historical versions compare
with explicitly resolved current. A single version has no previous action.
Base → target is always visible through sequence, timestamp and side labels,
stacked at narrow widths. Explicit comparison routes survive reload and source
navigation. Render factual added/removed Content, Evidence and recorded
interpretations separately from changed packet fields. No generated narrative,
strength inference, raw JSON or execution-noise changes. Empty comparison is
“无实质变化” / “No material changes”. Authority failures are localized and retryable.
Original excerpts and qualifications remain unchanged; exact historical source
ids stay navigable. Wrap quotations, long labels and revision context at 320px.

## Closure Settings and Following

Keep interface language separate from persisted output language. Use the existing
Panel, fields and buttons for explicit global focus/ignore/style editing. Following
shows inheritance or an explicit override; labels and errors are localized, while
source text and model names remain original. Preferences affect future checks,
never rewrite existing Summary/Evidence/Intelligence or Research snapshots.

Discovery, candidate preference, secure credential presence and read-only model
capability are distinct. Saving configuration cannot qualify, activate or dispatch
a model. Keep unavailable generation factual while existing library artifacts
remain usable. Password fields clear after save; deleting a Keychain credential
requires explicit confirmation. Keep success feedback visible across refresh.
Preserve six navigation destinations, wrapped controls and 320px layouts.

## Local provider imports

Following → Add retains the existing modal and offers YouTube or 本地文件 / Local
files. Use the native file input, explicit confirmation and individual results.
One Local library holds imported Content; no new primary navigation or watched
folder. Preserve snapshot and size-policy copy, filename wrapping, per-file errors,
and keyboard-accessible controls at 320px. Local collection detail has import and
Content navigation, without account or monitoring controls. Content uses the same
Summary/Evidence panels. Extractive Summary identifies original source excerpts;
media without a provisioned offline transcriber shows truthful unavailable status.
Text Evidence and Research use line ranges; timed media retains actual positions.
Provider labels are visible, original text is escaped plain text, and absolute
paths never appear in product presentation.
