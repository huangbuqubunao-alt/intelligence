---
name: Intelligence workspace
version: 1
---

# Intelligence workspace

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

## Layout and spacing

Use the existing dashboard stack and panels. Status and start/retry remain in the
Transcript panel; diagnostics use an expandable details disclosure. No primary
navigation is added. At 320, 768, 1024 and 1440 pixels all content must wrap without
horizontal overflow. Buttons use existing sizes and spacing.

## Interaction and accessibility

Use native buttons, labeled inputs and a keyboard-accessible details disclosure.
A polite live status announces transcription changes. Preserve source text,
Summary and Evidence reading order. Poll sequentially only during capability
checks or active jobs, at two-second intervals. No terminal instruction appears
in normal product flow.

## Language

All new controls and capability/status copy have zh-CN and English versions.
Machine reason codes belong in diagnostics; normal status uses localized copy.
Source language, output language and UI language remain separate.
