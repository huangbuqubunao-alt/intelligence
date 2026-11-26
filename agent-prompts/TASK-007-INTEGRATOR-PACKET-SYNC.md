# TASK-007 integrator-packet sync — Status Integrator

Create the final Product Integrator authorization only. This is a two-file control-plane commit: do not run product commands, modify source or access TASK-006.

- Main: `/Users/developer/Documents/youtubek agent`, `main@65f87c197cbc64ed18280bed99457244ebefa73e`, empty index.
- Accepted source: `/Users/developer/Documents/yia-worktrees/task-007`, `codex/task-007-local-scoring@95087c115b799d6f4e1e063a0adba0a6d10352ce`, clean; sole parent `9da12c2a6932d04b936d6ae1543acb55a72ec9dd`; review evidence only changes handoff.
- Confirm full `6b4d59c...95087c...` source range is exactly the 11 approved paths, Correction 3 exactly three paths, `pyproject.toml`/`uv.lock` unchanged, TASK-007=`ACCEPTED`, and `Mozhu <maintainer@example.invalid>` with `user.useConfigOnly=true`.

Stage/commit exactly:

1. `agent-prompts/TASK-007-INTEGRATOR-PACKET-SYNC.md`
2. `agent-prompts/TASK-007-INTEGRATOR.md`

Prepared-control exception: main is expected to contain exactly these two untracked paths. Record hashes, verify combined modified/untracked scope exactly, stage only them, repeat hashes after staging/before commit and compare staged blobs. Existing index content, extra path/hash change, identity/source mismatch blocks with no cleanup/overwrite/restage/commit.

Do not change statuses, prewrite merge/DONE, start Integrator or access TASK-006. Git/document checks only; no uv/tests/build/database/model/media/network. Commit `docs: authorize TASK-007 integration`. Report base/head, chain, scope/checks and clean main/source.
