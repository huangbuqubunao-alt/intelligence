---
name: Intelligence workspace
source: styles.css
---

# Workspace design reference: Home Knowledge Delta

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
localized and accessible. No History, Diff, chat, export or promotion control.
