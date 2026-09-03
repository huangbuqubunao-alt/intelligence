# FCC UI Design Reference

- Reference: `Alishahryar1/free-claude-code`
- Frozen commit: `0fb3b18ca8a21639ba7d1c2f11901217434eab6b`
- License: MIT, copyright Ali Khokhar (verified at the frozen commit)
- Reuse decision: `REFERENCE`

## Inspected presentation files

- `src/free_claude_code/api/admin_static/admin.css`
- `src/free_claude_code/api/admin_static/index.html`
- `src/free_claude_code/api/admin_static/admin.js`
- `src/free_claude_code/api/admin_static/chat_sessions.css`
- `src/free_claude_code/api/admin_static/chat_sessions.js`
- `src/free_claude_code/api/admin_static/model_combobox.js`

## Design mapping

| Area | Decision | First-party mapping |
| --- | --- | --- |
| Dark surface hierarchy | ADAPT | Near-black canvas, blue-gray panels, raised drawer/modal surfaces, low-contrast borders. |
| Typography and density | ADAPT | System font, compact 10–15px metadata/control scale, no external font. |
| Spacing, radius, shadow | ADAPT | 6/10/14px radius scale, 8px-based spacing, restrained elevation. |
| Shell and navigation | ADAPT | Sticky compact sidebar and quiet active treatment, retaining YouTube Intelligence IA. |
| Cards, tables, metadata | ADAPT | Compact workbench panels, scan-oriented rows, muted secondary metadata. |
| Buttons and fields | ADOPT | 38–40px controls, filled green primary, bordered secondary, quiet ghost, visible focus. |
| Status pills | ADAPT | Compact tinted semantic variants: success, warning, danger, info, neutral, blocked, ambiguous. |
| Transcript/history | ADAPT | Reading-width transcript and low-chrome vertical timeline; no chat UI. |
| Responsive behavior | ADAPT | Sidebar becomes scrollable top navigation; drawer and tables remain usable on narrow screens. |
| Provider configuration | REJECT | FCC provider/account controls are not applicable; this workspace only renders qualification projections. |
| Fixed action bar/chat/session UX | REJECT | This product has no corresponding write authority or chat IA. |

## Token mapping

The first-party CSS token layer follows the reference's surface relationship,
not its source: `--bg`, `--surface`, `--surface-raised`, `--surface-hover`,
`--input`, `--text`, `--text-strong`, `--text-muted`, `--border`,
`--border-strong`, `--accent`, `--accent-hover`, `--accent-soft`,
`--accent-border`, semantic status colors, radius, shadow, spacing, and
transition tokens.

## Attribution decision

No FCC source, assets, names, logos, distinctive copy, or screen layouts were
copied. The implementation independently reimplements high-level presentation
principles only. MIT attribution is therefore **not required** for shipped
source; this reference record preserves provenance.

## Intentionally not copied

Free Claude Code branding, app icon, provider/client/chat-session information
architecture, credential/account flows, fixed configuration action bar,
combobox code, external links, and all FCC-specific product language.
