# Design QA — Intelligence V1 Pre-freeze

**Implementation target**

- URL: `http://127.0.0.1:4178/demo-v1/?start=workspace`
- Key routes: `#home`, `#following`, `#following-ai-explained`, `#content-youtube-task-ui`, `#content-practical-ai`, `#content-youtube-pricing`, `#settings`
- Intended desktop viewport: 1440 × 1000 CSS px at device scale factor 1
- Intended narrow viewports: 820 × 1000 and 320 × 800 CSS px at device scale factor 1

**Implementation browser evidence**

- The live Demo returned HTTP 200 at `http://127.0.0.1:4178/demo-v1/?start=workspace#following`.
- Chrome computer-use automation failed twice while creating a controllable local tab. Per the failure policy, no screenshot, responsive visual-fidelity pass, accessibility-tree pass, network-panel pass, or console-cleanliness claim is made.
- Owner manual review can proceed against the live URL; automated component interactions cover all six updated pre-freeze paths.

**Automated validation evidence**

- TypeScript passed.
- All 21 Demo tests passed.
- All 34 frontend tests passed.
- Fixture relationship validation resolves stance coverage and every Following, Content, Evidence, Intelligence, Topic, and Research-version reference.
- Fixture validation enforces 18 Followings, the 7 / 4 / 3 / 4 Provider mix, one-layer Groups, non-empty Focus, and three complete Summary fixtures.
- The Summary fixtures cover: full Summary + Evidence + Intelligence + Topic; Summary with no Intelligence; and two Evidence from one video feeding one cross-source Intelligence.
- The Demo tests verify no `fetch` call during first-run and recovery.
- Static runtime scans found no network-call or browser-persistence APIs in the Demo source.
- Production build passed.
- `DESIGN.md` lint passed with zero errors and zero warnings.
- `git diff --check` passed; an explicit no-index whitespace check also passed for all untracked Demo files.
- Git status contains only the two allowed Demo directories; they were already untracked at task start.

**Updated owner paths covered by Demo tests**

- A — Following scale: 18 rows → AI Agent Group → new-Intelligence filter → paused filter → name search.
- B — Following Focus: AI Explained → default Preferences → per-Following override → Focus choices → content-processing choices.
- C — Content Summary: full Video Note → one-line Summary → six key points → timestamp chapter context.
- D — Summary without Intelligence: full Summary remains successful while showing “未发现值得长期保留的新洞察”.
- E — Summary to Intelligence: one video → E5 + E8 → one cross-source pricing Intelligence → Topic.
- F — Obsidian: connect mock → Video Notes selected → one-way Publish.

**Mock interaction boundaries**

- Group, filter, search, default/override settings, timestamp selection, detailed-summary generation, original-content links, backup/restore, and Obsidian publishing use only React browser state and short Demo-labelled timeouts.
- No action contacts a Provider, model, backend, database, filesystem, YouTube, or Obsidian.
- Advanced Model Settings alone shows the task mapping: Summary / chapters / key points → local low-cost; Intelligence → standard reasoning; Research → high-capability.

**Known UX validation gap**

- [P1] Browser-rendered visual QA remains unavailable.
  - Impact: typography, row density, overflow, breakpoint stacking, focus rendering, accessibility tree, request capture, and console cleanliness are not certified through the computer-use browser surface.
  - Owner can continue manual review against the live HTTP URL; no functional blocker was found by TypeScript, tests, fixture checks, build, or static side-effect scans.

final result: automated checks passed; browser visual QA unavailable; waiting for Owner final pre-freeze review
