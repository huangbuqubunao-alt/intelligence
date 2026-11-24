# TASK-READINESS-KIMI-PROVIDER-SETTINGS

Implementer `/root/bigmodel_audit_review` (new role for this task),2026-10-29.
Base `b080d26aa260eb02ca740427630fdb0670959f67`;
WT `/Users/developer/Documents/yia-worktrees/readiness-kimi-provider-settings`;
branch `codex/task-readiness-kimi-provider-settings`.
Suggested IN_REVIEW; Root alone accepts/integrates. Fixed SHA is the commit
containing this handoff, reported in chat. No subagents.

## Minimal result / reuse

DIRECT existing mutually exclusive credential editors, pending save guard,
provider-specific API/save/delete controls, ancestor-fold clearing and native
details/anchor navigation. REFERENCE existing BigModel Content-return whitelist;
the same narrow safe Content/Evidence shape is applied locally without changing
BigModel code or introducing a general route framework. No dependency or license change.
Read graph first, then current source because graph represented older editor code.
Read existing workspace DESIGN.md and reused existing Panel/details/field/button
styles; this copy/navigation change did not require a design-system rewrite.

- The provider section now says **Kimi / Moonshot API credential setup**, rather
  than tying a provider key to kimi-k2.6. Existing field/save/delete labels still
  name the Moonshot provider; the stored provider/API and actual execution model
  are unchanged. Scope is explicitly public YouTube Content only. Bilingual copy
  says a key does not select/activate a model or replace qualification, budget
  and separate authorization; saving still does not generate/upload Content.
- Exact `#Settings/models/moonshot` with optional safe Content/Evidence return is
  recognized at initial App entry and hash navigation. It opens every ancestor,
  focuses the Kimi editor and only mounts its password input. Existing metadata
  refresh is reused; no saved value is copied into a field.
- Existing BigModel↔Moonshot mutual selection remains. Hash changes clear drafts
  and deletion confirmations; ancestor folds unmount secrets and clear editor
  selection. Safe return accepts only internal Content/Evidence hashes without
  control/surrogate characters. External URLs, javascript, another Settings hash,
  fragment injection and a NUL target are rejected.
- Existing save/delete/pending functions are untouched. A provider switch/reload
  cannot transfer a secret draft or issue an autosave/model request. No model
  selector/runtime/backend/Schema/budget/credential configuration was added.

## Verification and preserved failures

All tests use fake fetch/stores and synthetic secrets. Only ignored own-WT
node_modules symlink reused Root's already installed modules; no package install,
dependency/lock/toolchain change, real Native/key/model/network or browser action.

- New focused checks first **9FAIL/1PASS**,175 not selected; failures reproduce
  missing Moonshot deep entry and old model-specific provider copy. Original log
  `/tmp/kimi-provider-settings-red.log` is retained. The shell printed its tail
  afterward; the actual Vitest summary is FAIL, not treated as exit-green evidence.
- After minimal implementation: **10PASS** focused Kimi cases; TypeScript PASS.
- Complete affected files ModelSettings, BigModelSettings and App:
  **202PASS10.55s**. Existing App tests emitted React act warnings from preexisting
  async/hash/Following cases; no warning filters or disabled assertions were added.
- Final added nested-ancestor folding test exposed a test fixture typing mistake:
  zero-argument vi.fn inferred a zero-length call tuple; comparing its length to1
  produced TS2367 in ModelSettings.test.tsx. Corrected only that new fixture to
  accept RequestInit and assert the meaningful condition, GET-only/no mutation.
  Final complete ModelSettings file **18PASS293ms**, final TS PASS. App168 and
  BigModel17/source files were unchanged after the202 complete run. These are
  separate results, not a claim of one combined203-test run.
- Production build `tsc -b && vite build`: PASS,53 modules,559ms. Only a test
  fixture was added afterward; product build source did not change.
- `git diff --check`: PASS.247 protected Python/SQL/scripts/fixtures/API/dependency
  and original BigModel implementation bytes checked against the fixed base.

Commands:

```sh
npm --prefix frontend run typecheck
npm --prefix frontend test -- src/workspace/ModelSettings.test.tsx src/workspace/App.test.tsx -t Kimi
npm --prefix frontend test -- src/workspace/ModelSettings.test.tsx src/workspace/BigModelSettings.test.tsx src/workspace/App.test.tsx
npm --prefix frontend run build
# After final nested-ancestor fixture addition:
npm --prefix frontend run typecheck
npm --prefix frontend test -- src/workspace/ModelSettings.test.tsx
```

Existing tests retain save/delete status and once-only double-click/inflight guards,
provider isolation, no copied/saved drafts, fresh metadata and ancestor cleanup.
Added cases cover English/Chinese direct entry, folded ancestors, invalid returns,
same-page hash changes, unmount/reload, Content Evidence return and no automatic writes.
Existing test text expectations were updated only for the deliberately renamed
provider section; no safety assertion was removed or weakened.

## Limits / disposition

Only ModelSettings/App's narrow route branch, exact bilingual copy, relevant tests
and this handoff changed. No Python, SQL, execution/qualification policy, API client,
BigModel provider implementation, runtime settings, credentials, owner data or main
changed. No real GUI/autofill/Keychain/provider/account-quality/billing proof is claimed;
tests are component DOM/fake API evidence. Full frontend suite is left for Root's
once-after-integration run per task, not repeatedly run here.

Scoped commit, clean STOP. Root's independent narrow review remains required.
