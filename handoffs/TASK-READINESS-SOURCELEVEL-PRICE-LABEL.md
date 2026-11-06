# Source-level price selection follow-up

Implementer `/root/v3_price_label` completed the bounded follow-up assigned by Root on 2026-11-07. Base `73669f0fcd53fe3667d08d98a6ecee8684f6c3f7`, worktree `/Users/hua/Documents/yia-worktrees/readiness-source-level-synthesis-v3`, branch `codex/readiness-source-level-synthesis-v3`. Root owns independent review and integration.

## Goal and reuse

Make the existing spending settings accept the three declared backend profiles, distinguish the source-level policy in English and Chinese, and retain explicit acknowledgement of the selected price. DIRECT reuse of the existing component, finite profile checks, translation key, request endpoint and test harness. Existing project code only.

Inspection found that the component rejected catalogs longer than two entries and allowed only v1/v2. A real three-profile response therefore prevented the spending form from rendering, before the misleading fallback label could appear. Root confirmed this decoder correction belongs to the assigned component scope.

## Changes

- `CloudSpendingSettings.tsx` accepts up to three entries in its fixed catalog and adds the exact v3 profile ID. The v3 option uses the existing `Source-level attribution` translation. Existing validation still rejects unknown profiles and duplicate IDs.
- `CloudSpendingSettings.test.tsx` adds the three-policy positive path, all three distinct names, v3 selection clearing acknowledgement, exact v3 price hash on save, preserved draft and held reservation, Chinese naming, and unknown/duplicate/fourth-entry rejection.

## Verification

| Check | Result |
|---|---|
| Added regression tests against the original component | 2 FAIL, 17 PASS. Three-policy form absent and Chinese v3 option absent. Preserved in `.var/source-level-v3/price-settings-red.log`. |
| `npm --prefix frontend test -- src/workspace/CloudSpendingSettings.test.tsx` after fix | 19 PASS, 1.23s. `.var/source-level-v3/price-settings-green.log`. |
| `npm --prefix frontend run typecheck` | PASS. `.var/source-level-v3/price-settings-typecheck.log`. |
| `git diff --check` | PASS. |
| Scoped diff review | Two frontend files and this handoff. |

Root is running the actual browser verification separately. This focused follow-up did not rerun full frontend/backend suites. Those final combined checks belong to the integrated candidate. Worker performed zero model, network, Keychain or fee operations. Suggested state `IN_REVIEW`; scoped commit SHA is reported in the task response.
