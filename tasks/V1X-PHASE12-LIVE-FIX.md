# Phase 12 live YouTube baseline P0 remediation

Owner-authorized sole-executor goal. Start exactly at failed candidate
`d0679d50b3a7a0f2e8a3006fdab8ccc268614a18`, branch
`codex/phase12-live-fix`, isolated worktree `phase12-live-fix`, schema 34.
The prior candidate is not an accepted final Phase 12 baseline. Its main
adoption gate is blocked. No merge, push, PR, Phase 13 or Phase 14 is authorized.

Scope: reproduce the independently observed real Atom contract, correct the
feed-level comparison without relaxing canonical source or entry membership,
add realistic regression fixtures, validate the existing tracking lifecycle,
run all required regressions and integrity checks, attempt bounded production
transport validation, self-review and locally commit the new candidate.

Reuse DIRECT: standard-library XML parsing; existing canonical_channel and
strict shared RSS entry parser; shared Following ledger/frontier; ordinary
Content enrollment/transcript/Summary/Evidence; Source Run and Backup/Restore.
No new dependencies, migrations, network policies or authority subsystem.
REJECT/DEFER: suffix/substring matching, advisory-only feed identity, ambient
proxy support, credentials/cookies, scraping fallback and provider expansion.

Protected worktrees: original Phase 12, Phase 12 resume, independent live
validation and dirty M13. Record actual fingerprints before product edits;
require exact equality at completion. Preserve existing dirt without cleanup.

Evidence and self-review: `docs/validation/phase12-live-fix/`.
The realistic fixtures are synthetic entries with the independently observed
NASA identity shape, not captured live content or claims of a real upload.
Independent live acceptance remains a separate gate from fixture success.
