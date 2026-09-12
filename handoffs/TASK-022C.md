# TASK-022C Handoff — Resource Ledger AMBIGUOUS Outcome Amendment

## Metadata

- Task: `TASK-022C — Resource Ledger AMBIGUOUS Outcome Amendment`
- START_HEAD: `7a63c12cf9b7bbc85127f454455cfa1f610ae18d`
- Database: `v015 -> v016`; `m016` added; `m017` absent.
- No provider, YouTube, or other external network operation was invoked.

## Delivered contract

m010 remains byte-for-byte unchanged.  m016 reconstructs only
`distillation_resource_usage`, copies every existing column verbatim, and
recreates both append-only triggers.  Its existing finite `status` CHECK
continues to include `AMBIGUOUS`; the new identity pairing check permits
`actual_provider` and `actual_model` to be simultaneously unknown only for an
invoked `AMBIGUOUS` row.  Every other invoked row still requires both actual
identities, and every uninvoked row still requires neither.

The runtime now persists transport uncertainty without inventing the selected
model as an actual model.  `AMBIGUOUS` remains terminal: checkpoint terminal
immutability, TASK-023B continuation, restart recovery, budget ordering, no
fallback, and zero redispatch behavior are unchanged.

## Verification

| Check | Result |
| --- | --- |
| Focused TASK-022/023B/state/migration/doctor tests | `99 passed` |
| TASK-018B through TASK-021 regression group | `76 passed` |
| Full pytest | `2209 passed, 1 skipped, 1 existing Pydantic serializer warning` |
| `uv run --offline mypy src` | PASS, `54` source files |
| `uv run --offline ruff check .` | PASS |
| `uv build --offline` | PASS; existing build-system-version warning |
| Fresh DB and v015→v016 probe | PASS; 16 migrations, two ledger immutability triggers, no FK violations |
| Packaged migration inspection | PASS; m015 and m016 present |
| m010 checksum against predecessor | unchanged |
| `git diff --check` | PASS |
| Security scanner | EXIT `1`; 11 accepted historical synthetic-fixture findings, 0 new; not PASS |

## Adversarial result

P0: `0`  
P1: `0`  
P2: `0`

Checked: unknown actual identity is accepted only for durable `AMBIGUOUS`;
arbitrary statuses and non-ambiguous unknown identity fail SQL checks;
historical ledger rows, FK metadata, and indexes are preserved; update/delete
remain blocked; a terminal ambiguous execution cannot redispatch on duplicate
continuation or restart; no provider/model fallback, semantic retry, cost-zero
fabrication, credential persistence, cloud enablement, Deep Analysis, or
TASK-016G authorization was introduced.

## Next authorized action

TASK-022A may restart only from the approved TASK-022C commit.  This task does
not itself authorize cloud transport or provider qualification.
