# TASK-READINESS-BIGMODEL-TRANSPORT-REVIEW

## Metadata and verdict

- Reviewer: `/root/bigmodel_audit_review`, independent fixed-source review; no subagents.
- Accepted comparison base: `523bff80d343949f57159b94e10ed1c4328144e5`.
- Reviewed author: `a7a9d710816c316e5719f9fcf5ed8da0b9b80e57`.
- Review baseline: `b893762dbc38eafa0f714dc5592c5d2045daa3b1`, only Root task/prompt added to author source.
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-bigmodel-transport-review`.
- Branch: `codex/task-readiness-bigmodel-transport-review`.
- Date: 2026-10-27.
- **Verdict: REJECT fixed a7, one confirmed P2; no confirmed new P0/P1 in the bounded slice.** Root and original writer were notified immediately. Any later repair requires its own fixed-source review; it is not reviewed by this report.

Only this report was written. Product source, tests, SQL, configuration, credentials, Root services, owner data and main were not modified. No real HTTP/model/key lookup occurred; all key strings and responses below are offline synthetic fixtures.

## Finding P2-01 — reject an unsendable projection before credential preflight

Location: `src/youtube_intel/distillation.py:4734` through the model readiness call at4741, new adapter permission at2497 and credential preflight at2508. `generate` correctly calls the pure `_request` before its own credential resolution, but the reserved service has already called `_model_ready` → `preflight_available` by then. The permission predicate checks source/pair/hash/one-call authority but does not validate the frozen wire-input bound.

With a legitimately bound public caption exceeding128KiB, normal reserve, exact qualification permit and OWNER_QUALIFICATION consent all succeed. Pure `_request` rejects the input. Continuing the reservation nevertheless resolves the credential, claims the task, and only then rejects it as `WAITING_MODEL`, count0, `CLOUD_CREDENTIAL_REQUIRED_BEFORE_DISPATCH`. Thus an input-size refusal becomes a misleading missing-credential state, and an input that is known to be unsendable crosses the task's explicit pre-credential denial boundary. No POST was observed and there is no evidence of private upload or duplicate invocation in this reproduction.

Minimal correction: for only the new pair, validate the same pure request projection before credential preflight/claim, retaining the exact permit/consent/current-input checks and old adapter behavior. Persist the real input refusal through an existing safe terminal status/outcome with count0; retain consent, Evidence and DATA, avoid orphan PENDING, fake success, replay or a new lifecycle. Do not simply return false from model availability and keep the misleading credential explanation.

### Independent reproduction

Use the existing interpreter and explicit review import paths:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/Users/hua/Documents/yia-worktrees/readiness-bigmodel-transport-review/src:/Users/hua/Documents/yia-worktrees/readiness-bigmodel-transport-review/tests/integration \
/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import test_task022_personalized_distillation as f
from test_bigmodel_distillation_transport import _setup, _permit
from youtube_intel import distillation as d

text = 'Public caption factual sentence. ' * 5000
cue = f.TimedTranscriptCueWrite
bind = f.EvidenceTextBindingWrite.from_timed_transcript
with TemporaryDirectory(prefix='bigmodel-review-evidence-probe-') as t:
    keys, wires = [], []
    with patch.object(f, 'TimedTranscriptCueWrite', side_effect=lambda **kw: cue(**dict(kw, text=text))), patch.object(f.EvidenceTextBindingWrite, 'from_timed_transcript', side_effect=lambda **kw: bind(**dict(kw, excerpt=text))):
        repo, source, video, evidence, service = _setup(Path(t), wire=lambda *a: wires.append(a), credentials=lambda: keys.append('credential') or 'synthetic')
    r = service.reserve_distillation_execution(source_id=source, video_id=video, evidence_ids=(evidence,))
    _, v = service._reserved_command_from_record(repo.get_distillation_execution(r.execution_id))
    _permit(service, v)
    service.authorize_reserved_cloud_execution(r.execution_id, consent_kind='OWNER_QUALIFICATION')
    try:
        service._transport._request(v)
    except d.CloudDistillationPreDispatchError as e:
        print('pure refusal:', str(e), 'excerpt bytes:', len(v.evidence[0].excerpt.encode()))
    result = service.continue_qualification_reserved_distillation(r.execution_id)
    print('result:', result.status.value, 'count:', result.invocation_count, 'key lookups:', len(keys), 'wire calls:', len(wires))
    print('usage outcome:', repo.get_distillation_resource_usage(r.execution_id).outcome)
    assert result.status.value == 'WAITING_MODEL' and result.invocation_count == 0 and len(keys) == 1 and not wires
PY
```

Actual exit0 output:

```text
pure refusal: BigModel input exceeds its UTF-8 bound excerpt bytes: 165000
result: WAITING_MODEL count: 0 key lookups: 1 wire calls: 0
usage outcome: CLOUD_CREDENTIAL_REQUIRED_BEFORE_DISPATCH
```

This uses the existing trusted TimedTranscript/EvidenceTextBinding constructors, changing only the public fixture's literal text. No schema/trigger/authority corruption or actual credential is involved. An earlier caption probe printed the same counterexample, then incorrectly read nonexistent `record.outcome` in an auxiliary print (exit1). The corrected reproduction above reads the existing resource-usage projection and exits0. A separate initial long-title probe also confirmed the boundary; the trusted caption case is the stronger evidence.

## Scope, architecture and security review

Read repository instructions, collaboration/status, PRD/system design, V1 product scope, reuse register, the transport task/prompt/handoff, three-path amendment/free-cloud preflight, audit migration plan and accepted audit/claim review histories. Used code-review-and-quality and security-and-hardening skills. Graph discovery identified the common authorization/readiness/continuation methods; current source/AST supplied the newer adapter absent from the indexed graph. Jev was unavailable; the existing strong independent review was retained.

The complete four-file base→author diff contains one production file, two new offline test files and the implementer's handoff. No SQL/dependency/lockfile/runtime/API/UI/settings/credential/budget/owner/main edits. Standard-library TLS/HTTP/JSON/threading and existing sealed-input, consent, claim, decoder, admission and accounting are DIRECT reuse; fixed provider protocol is REFERENCE. No new SDK/license obligation or generic provider framework.

Reviewed frozen exact pair/host/path, nonstream/thinking/JSON/max16384/temp1/300s/zero-retry/input and response limits; canonical profile/input/reservation binding; source denials and generic/normal production denial; immutable consent checks; pre-dispatch versus unknown POST accounting; bounded body and absolute read deadline; late DNS connector prohibition on POST; retained detached socket shutdown; redirect refusal and lack of retry/fallback; exact one assistant final/model/stop, malformed JSON/usage handling; public-final-only projection and reasoning/secret suppression. The new normal-production predicate remains false and no existing qualified model authority is transferred. Apart from P2-01, no further confirmed defect was found in this bounded review. This is not a claim that every possible network stack behavior has been physically exercised.

AST comparison independently verifies42 old adapter/parser/shared-prompt method segments byte-identical to523b. All41 packaged SQL files (001–042, no029) are byte-identical. All435 tracked src/tests files match author a7. Combined sorted path+bytes SHA256: `bf23737c65f5b61d46cb98a841f5cb6f98fd57f4d79e7820bf381d0b3c7fca3a`.

## Independent checks

All Python checks use `PYTHONDONTWRITEBYTECODE=1`, explicit review `PYTHONPATH=/Users/hua/Documents/yia-worktrees/readiness-bigmodel-transport-review/src` and `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`. Fixtures create their own temporary DB/DATA. Compile was run before tests.

| Check | Result |
|---|---|
| In-memory compile all src Python |122files PASS |
| Full12-file affected pytest group below |**578PASS**,408.14s, exit0; one expected duplicate-path ZIP fixture warning |
| `python -m mypy --strict src` |122files PASS |
| `ruff check --no-cache src/youtube_intel/distillation.py tests/unit/test_bigmodel_distillation_adapter.py tests/integration/test_bigmodel_distillation_transport.py` |PASS |
| `git diff --check 523bff80d343949f57159b94e10ed1c4328144e5 a7a9d710816c316e5719f9fcf5ed8da0b9b80e57` |PASS |
| Independent unsendable trusted-caption counterexample |Confirmed P2-01, zero wire/model calls |
| Source/test equality, old-method AST and SQL byte checks |PASS as above |

Complete pytest argument list (one command after the interpreter/environment prefix):

```text
-m pytest -p no:cacheprovider
tests/unit/test_bigmodel_distillation_adapter.py
tests/integration/test_bigmodel_distillation_transport.py
tests/unit/test_moonshot_distillation_adapter.py
tests/unit/test_openai_distillation_adapter.py
tests/unit/test_distillation_dispatch.py
tests/unit/test_bigmodel_claims.py
tests/integration/test_task022_personalized_distillation.py
tests/integration/test_task023b_distillation_reservation.py
tests/integration/test_distillation_source_context.py
tests/integration/test_local_intelligence_timed.py
tests/integration/test_local_intelligence_text.py
tests/unit/test_backup_restore.py -q --tb=short
```

Author's original574PASS1FAIL and additional consent3RED→GREEN remain separate historical evidence, as does its final578PASS. They are not relabeled as the reviewer's run or added as disjoint totals. The independently rerun full group passes but omits the confirmed pre-credential size counterexample; the green count does not override P2-01. Source/tests still match fixed a7 after the run. No tests/assertions were deleted, skipped or weakened. Full whole-project regression/build/GUI is outside this backend-only review slice; Root retains those later gates.

## Remaining gates

This rejection is bounded engineering feedback, not a new approval request or model experiment. Root has returned the correction to the original writer. Normal GLM quality qualification and production budget remain closed. No real account entitlement/zero bill/quota/network generation/semantic quality/ordinary-user chain was verified by this review. Existing offline admitted/NO_NEW fixtures and Root's unauthenticated HEAD401 cannot establish model qualification. Real public-sample acceptance, provider-isolated safe key input, user disclosure/consent, restart and full Backup/Restore, final whole-feature checks and safe main adoption remain Root-owned gates.

Reviewer recommends **REJECT a7 pending P2-01 correction and independent fixed-delta verification**. No integration, production configuration or user-data action was performed.
