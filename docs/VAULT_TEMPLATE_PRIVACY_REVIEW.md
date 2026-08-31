# Vault and Template Distribution-Boundary Privacy Review

## Scope and disposition

- **Review baseline:** `main@735a014` (2026-08-31).
- **Scope:** the current private/proprietary controlled first-party source
  repository, sdist, and wheel boundary; the runtime Vault, fixed package
  templates, generated Note/Weekly outputs, credentials, logs, errors, cache,
  and provenance.
- **Excluded:** real Vault or user-note access, live providers or credentials,
  provider qualification, scanner redesign, packaging redesign, public release,
  bundle/container/installer distribution, push, and tag.
- **Privacy technical review:** **APPROVE** for the current controlled target.
  No P0 or release-critical technical P1 Vault/template distribution defect was
  found.
- **Independent human Privacy Reviewer signature:** **OPEN**. This is technical
  evidence only; it records no named reviewer, human signature, legal approval,
  or final release approval.

## Recovered privacy and distribution contract

The PRD prohibits committing real tokens, private subtitle bodies, and personal
Vault content. ADR-002 requires project-relative `data_dir`, `logs_dir`, and
`templates_dir`, while `vault_root` is a runtime-only absolute configuration
value and `vault_subdir` is a safe relative child. ADR-009 requires package-fixed
templates, a directory-FD-anchored Vault writer, relative `NoteRef` paths, and
safe errors without absolute Vault paths. ADR-010 applies the same fixed-template
and temporary-Vault-only rule to Weekly reports. ADR-027 and the persisted
Deep-Analysis contract keep credentials and credential references out of
identities, cache, provenance, logs, and errors.

The current artifact boundary is unchanged: the controlled first-party source
repository, sdist, and wheel are in scope; dependencies are separately resolved
by the package manager. A materialized environment, bundle, container, installer,
or public distribution is not authorized.

## Data inventory and runtime boundary

| Data surface | Classification | Runtime location / handling | Distribution result |
| --- | --- | --- | --- |
| Package templates | First-party static | `src/youtube_intel/templates/{video,weekly}.md`, loaded read-only through `importlib.resources` | In wheel and sdist; inspected static placeholders only |
| Vault root and managed subdirectory | User-specific operational metadata | Required runtime config; rooted writer accepts only an absolute root plus safe relative child | Not a package input or archive member |
| Rendered video notes / user-editable region | User-specific | Written atomically beneath the anchored Vault `Videos/` directory | Not tracked or archived |
| Generated weekly reports | User-specific | Written atomically beneath the anchored Vault `Weekly/` directory | Not tracked or archived |
| Transcript text / provider responses | User-specific, potentially sensitive | Runtime `data/` and validated persistence only | No tracked runtime tree, wheel, or sdist member |
| SQLite / cache | Operational metadata and possible user-specific content | Runtime project-relative `data/`; rows use relative artifact paths | No tracked database/cache or archive member |
| Credential reference | Operational metadata | Configuration permits an environment-variable name, not a value | No resolved value in templates, archives, cache, provenance, logs, or errors |
| Resolved credential value | Secret | Runtime-only provider boundary | No distribution or persistence surface |
| Logs and safe errors | Operational metadata | Runtime project-relative `logs/`; sanitizer redacts secret-shaped values and paths | No tracked log or archive member |
| Examples and tests | Test-only | Tracked synthetic corpus, excluded from wheel/sdist | Not runtime assets; the pre-existing scanner exception remains limited to its exact 11 findings |

`ObsidianNoteSink` reads fixed templates only to render a new managed region. It
writes with directory descriptors beneath `vault_root/vault_subdir`, records only
a validated relative path in `NoteRef`/artifact metadata, and merges an existing
user region without writing back to a package template. The Weekly writer uses
the same anchored-root approach. Note V2/Weekly V2 are deterministic in-memory
presentations; their tests show unselected transcript material is absent from
the Note, artifact representation, identity, and rendered Weekly output.

## Distributed templates and build inputs

Exactly two application templates are distributed:

| Template | Purpose | Archive presence | Inputs |
| --- | --- | --- | --- |
| `src/youtube_intel/templates/video.md` | Managed Obsidian video-note region | wheel and sdist | Fixed Jinja placeholders for already validated runtime primitives |
| `src/youtube_intel/templates/weekly.md` | Managed Weekly report | wheel and sdist | Fixed Jinja placeholders for verified report items and aggregates |

Direct template inspection found placeholders/control markers only: no literal
user name, email, credential, Vault location, hostname, machine identifier,
absolute user path, transcript, generated note/report, or resolved secret. The
launchd examples use only `__PROJECT_ROOT__`; `config/settings.example.yaml`
uses the generic `/absolute/path/to/obsidian/vault`, not a user location.

`pyproject.toml` has no runtime-data include rule; its only explicit
`source-include` entries are the static launchd examples and `docs/operations.md`.
`.gitignore` anchors `/data/` and `/logs/` at repository root. The build is
therefore both configured and empirically verified not to include a Vault,
rendered outputs, databases, caches, tests, dependency wheels, or copied
`site-packages`.

## Offline artifact and sentinel evidence

`uv lock --check`, `uv sync --locked --offline`, and `uv build --offline` ran
against the reviewed baseline. The fresh build contained a 62-member wheel and
a 68-member sdist. Direct member and content inspection found:

- the two static templates above in both artifacts;
- no Vault, rendered note/report, transcript, database, cache, log, test,
  dependency wheel, or `site-packages` member;
- no `/Users/...` or `/home/...` content fragment in either archive;
- zero occurrences in both artifacts for six synthetic privacy sentinels:
  a user marker, email marker, Vault marker, transcript marker, credential
  reference marker, and non-secret resolved-value marker; and
- no `o200k_base.tiktoken` archive member or binary payload. Its literal name
  remains an expected source-code/documentation reference to ADR-028's external
  provisioning rule, not a distributed tokenizer file.

Focused runtime evidence was also rerun with synthetic-only values:

| Control | Evidence |
| --- | --- |
| Persisted Deep Analysis | Secret and unselected-transcript sentinel absent from serialized database row |
| Job/provider errors | Secret-shaped values and raw response body absent from persisted error fields |
| JSONL logging | Path and secret-shaped values redact to a bounded safe message |
| Note persistence | Atomic-write failures expose a fixed safe message and preserve the existing temporary-Vault note |
| Weekly V2 | Unselected-evidence sentinel absent from Note, artifact, identity, and rendered report |
| Path/provenance | Escaping or provenance-mismatched note references fail closed before Weekly write |

The focused Vault/template/persistence suite passed **180 tests**; the selected
synthetic privacy and error tests passed **13 tests**. All use pytest temporary
directories and no real Vault, credential, provider, or network call.

## Release regression evidence

| Check | Result |
| --- | --- |
| `uv lock --check`; `uv sync --locked --offline` | PASS |
| Focused Vault/template/persistence tests | `180 passed` |
| Selected synthetic privacy/error sentinels | `13 passed` |
| Full pytest | `1920 passed, 1 skipped, 1 warning` |
| `uv run mypy src` | `Success: no issues found in 40 source files` |
| `uv run ruff check .` | PASS |
| Scanner regression | `20 passed` |
| Canonical scanner | `EXIT 1`; exactly the 11 previously accepted intentional-positive fixtures, not PASS; new privacy/security findings `0` |
| Offline wheel and sdist | PASS; fresh 62-member wheel and 68-member sdist inspected directly |
| CLI help | `youtube-intel --help` and `youtube-intel doctor --help` PASS |
| `git diff --check` | PASS after documentation updates |

## Controlled-source nuance

The controlled full Git source tree is not equivalent to the sdist. Its current
tree contains historical agent-governance material with contributor/worktree
metadata, including email-like and absolute-home-path strings. They are neither
Vault contents nor runtime outputs, are outside the package and sdist source
set, and were not copied into the wheel/sdist. They remain a **P2 source-history
privacy hygiene risk** for any future broader/public source distribution; this
review neither removes historical audit records nor treats them as packaged
content. No real Vault data, user note, transcript body, credential value, or
provider response was identified in the current package source set.

## Adversarial review and re-review triggers

The review challenged accidental Vault/database/log inclusion, rendered-template
write-back, transcript/provider-output packaging, literal paths/identifiers in
templates, credential leakage through templates/errors/logs/cache/provenance,
source-vs-sdist conflation, and misuse of the existing finite scanner exception.
Current static traces, source inventory, archive inspection, and synthetic tests
reject each attack for wheel/sdist and the production runtime boundary.

**P0: 0. Release-critical technical P1: 0. P2: 1** (historical controlled-Git
governance metadata, not a runtime/Vault/package artifact).

Re-review is required if a template, build include/exclude policy, Vault writer,
rendering destination, persistence/logging/credential surface, source
distribution policy, or distribution mode changes; if an archive gains a
runtime/user artifact; or before any public, bundle, container, installer, or
copied-environment distribution.
