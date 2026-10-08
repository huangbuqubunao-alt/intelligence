---
name: Intelligence workspace
source: styles.css
---

# Workspace design reference

Phase 13 uses the same Following detail: next automatic check and explicit retry
eligibility are separate facts. Background backoff does not hide manual network
recovery. Automatic checks operate while the backend runs, including with the
browser window closed. Preserve bilingual wrapping and the existing buttons;
add no scheduler controls, navigation, or notification platform.

Phase 10B adds Bilibili to Following Add and the existing shared Content/Research
surfaces. Manual video import never implies creator following. Public captions
retain original text/language/timing; no-caption Content explains unavailable
Summary/Evidence and offers explicit retry. Show publication time and uploader;
internal metadata artifact formats stay out of the reading UI. Use bilingual
labels, plain text and wrapping without adding primary navigation or provider
polling. Root `DESIGN.md` records the persistent import interaction contract.

Reuse the live workspace's dark surfaces, green accent, muted typography, Panel
borders, radius tokens and button styles from styles.css. Do not redesign Home.

## Creator Following

Phase 11 keeps “添加一个视频 / Add one video” and “关注一个 UP 主 / Follow a
creator” distinct inside the existing Bilibili Add modal. Explain following from
now on, the bounded starting point and application-only checks before submission.
Content may offer “关注此 UP 主 / Follow this creator” using verified metadata.
Creator detail uses the same modal, buttons and metadata rows: last check, last
successful check, human-readable health, cumulative discovered Content, pending
acquisition, Check Now and pause/resume. Counts are factual, never unread badges.
Show linked ordinary Content; do not introduce a feed, notification center or
primary destination. Existing Following filters use durable discoveries, trusted
Intelligence and actual processing/health states. Wrap titles and health copy at
320px; preserve plain-text rendering and Chinese/English symmetry.

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

## YouTube channel Following

Phase 12 reuses CreatorFollowing's form and detail for public YouTube channels.
Add keeps one-video import distinct from channel follow. A channel cannot enter
through the one-video form. Explain a bounded baseline that imports zero history.
Provider-scoped canonical identity is invisible implementation authority; show
channel name, provenance, last complete check and truthful health. Handle/name
changes reuse the same source. Content offers Follow this channel from trusted
metadata. Existing filters, Check Now, pause/resume and ordinary linked Content
work identically across providers. Timed public captions use the shared transcript
view. Do not offer local acoustic transcription for missing YouTube captions.

Following rows label ordinary VIDEO_URL entries as manually imported videos,
so a video import sharing a channel display name remains distinguishable from a
tracked channel. Update/insight/attention/paused filters use actual shared state.

## Validated baseline integrated into Phase 12

Bilibili creator Following is withdrawn under Phase 11R.1. Keep stored detail and
pause/resume preferences, but show unavailable current capability and disable
Check Now and creator enrollment. Historical source health is labeled as recorded
history. YouTube uses the same tracking form/detail and its own capability; Bilibili
withdrawal must not disable channels. A check's running notice is replaced by its
settled health. Show the next eligible check without implying a scheduled daemon.
