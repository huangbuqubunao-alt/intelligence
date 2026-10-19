---
name: Intelligence workspace
version: 1
---

# Intelligence workspace

Phase 13 keeps the existing Following detail and controls. Show the next
automatic check separately from explicit retry eligibility; background network
backoff must not disable the accepted five-second user retry. Healthy tracking
requires no settings. Checking, paused and attention remain ordinary localized
states. The backend owns scheduling while it runs; no scheduler administration
surface or OS service installation is introduced.

## Design intent

A quiet, local knowledge workspace. Follow the existing Following, Content,
Intelligence, Topic and Settings layout. Source authority stays visible while
engineering diagnostics remain secondary.

## Colors

| Token | Value | Use |
| --- | --- | --- |
| Background | #090b10 | Workspace canvas |
| Surface | #11151d | Content panels |
| Text | #e9edf2 | Primary reading text |
| Accent | #32ae79 | Primary action |

The existing workspace CSS is the implementation reference; Phase 8 uses its
button, panel, hint and semantic status classes without adding a visual theme.

## Typography

Use the system sans-serif stack already defined by the workspace. Preserve the
existing title/body/hint hierarchy. Transcript words stay exact; source timestamps
use a smaller line above each segment. Long model identities wrap within the
Content panel.

Local media metadata wraps into readable rows on narrow screens. Its header and
Transcript panel use the same live transcription status. Suppress the historical
unavailable placeholder when the live Local transcription surface is present.

## Layout and spacing

Use the existing dashboard stack and panels. Status and start/retry remain in the
Transcript panel; diagnostics use an expandable details disclosure. No primary
navigation is added. At 320, 768, 1024 and 1440 pixels all content must wrap without
horizontal overflow. Buttons use existing sizes and spacing.

## Interaction and accessibility

Local import failures and completion are notices for the current operation.
Do not replay terminal job history when loading the workspace. Results shown in
the import dialog are not duplicated above every page. A background completion
can be dismissed and expires after 15 seconds; navigation clears terminal
notices while genuine active imports stay visible. Acknowledging a notice never
cancels a job or deletes its history.

Introduce speech readiness during onboarding and before local import. Blocked
audio/video Content links to Settings → local transcription and back to the
same Content. Explain runtime, missing model and acoustic verification separately.
Only the backend's production eligibility permits transcription. Saving a model
directory is a configuration action, never proof that transcription is usable.
Status refreshes must not erase operation failures before the user can read them.
Content list and detail use the canonical URL so refresh and browser history
preserve the reading location.

Use native buttons, labeled inputs and a keyboard-accessible details disclosure.
A polite live status announces transcription changes. Preserve source text,
Summary and Evidence reading order. Poll sequentially only during capability
checks or active jobs, at two-second intervals. No terminal instruction appears
in normal product flow.

## Language

All new controls and capability/status copy have zh-CN and English versions.
Machine reason codes belong in diagnostics; normal status uses localized copy.
Source language, output language and UI language remain separate.

## Acoustic qualification diagnostics

Phase 9 adds one acoustic qualification row to the existing Transcript diagnostics
disclosure: not tested, running, passed, failed or stale. Model availability stays
separate. Unqualified installed models cannot start new production transcription;
existing trusted text, Summary and Evidence remain readable. No Settings switch
or navigation destination issues a qualification receipt. Benchmark detail stays
in engineering acceptance evidence. All states have zh-CN and English copy.

## Public Bilibili video import

Following Add offers YouTube, Local files and Bilibili in the same dialog flow.
Bilibili imports one explicitly supplied public video; the source label says
manually imported video and never implies creator monitoring. The shared Content
page shows Bilibili provenance, uploader, publication time, duration, source
language and caption status. No primary navigation or separate provider page.

Original timed captions appear in the existing Transcript, Summary and Evidence
panels. Metadata-only Content explains why Summary and Evidence are unavailable
and offers an explicit public-caption retry. Reading trusted stored captions makes
no provider request; no active polling or acoustic fallback is offered. Ready
authority has no refresh control. Long untrusted title and caption text renders as
plain text and wraps at every supported viewport. Labels and failures use the
existing Chinese and English UI dictionary; caption language stays independent.

## Continuous Following across providers

YouTube channel and Bilibili creator use one Following list, filter and detail
interaction. Provider is provenance. YouTube Add distinguishes one video from
“关注一个频道 / Follow a channel”; channel following explains “from now on” and
never offers implicit historical backfill. Trusted Content offers “关注此频道 /
Follow this channel”. Channel titles and handles are presentation aliases;
canonical channel identity governs deduplication.

Both providers share Check Now, pause/resume, last complete successful check,
health and ordinary discovered Content. Missing captions retain honest transcript
and Summary/Evidence states, without offering an acoustic fallback. Render trusted
timed YouTube captions using the existing transcript view. Preserve all six primary
navigation buttons, bilingual labels, wrapping and 320–1440px layouts.

## Phase 12 resume capability authority

The validated Phase 11R.1 baseline supersedes the historical Bilibili creator
availability descriptions above. YouTube channel Following remains available
through the shared tracking UI; Bilibili creator Following remains withdrawn.
Stored Bilibili sources and Content stay readable. Do not offer creator enrollment
or active checks. Distinguish current capability from last recorded source health.
Check Now shows its running and settled outcome, cooldown and next eligible check.
A cooldown timestamp is eligibility, not a promised background schedule.

## Phase 12 automatic YouTube network compatibility

YouTube Following has no network settings or transport selector. Use the current
macOS network automatically. An offline add/check shows “无法连接 YouTube。请检查
网络或 VPN 后重试。” / “Unable to connect to YouTube. Check your network or VPN
and try again.” Keep input and an explicit Retry on add failure; stored offline
channels offer Retry when eligible. A created source is distinct from a successful
baseline: show the offline message even when creation succeeded but the initial
feed check failed. Preserve existing modal/button styles and wrapping at 320px.
Never render backend socket, proxy or resolver details.

## Backup safety feedback

Backup lists every returned blocking reason. Distinguish unfinished work from
unverified database or stored-file integrity; unknown reasons remain neutral and
closed. Use bilingual finite copy without backend paths or raw errors. Caption
retry completion refreshes dependent Evidence and Deep Analysis reads in place.
