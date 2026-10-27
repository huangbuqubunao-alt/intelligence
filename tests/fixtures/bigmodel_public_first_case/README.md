# Offline public BigModel diagnostic stock

This **test-only** archive makes `test_bigmodel_public_first_case.py` independent of any
Root worktree, `.var` directory, credential store, network or saved model response.
It was frozen on 2026-10-28 from the task-authorized public/synthetic diagnostic copy
used by producer commit `14565034a3c3e20714bc7448c514f43132be86ff`.
The real one-shot package and its execution script are separate and unchanged.

`stock.zip` SHA256: `f12f59025ef423fb0a3b6b0bd74e33b46846d481879bf8cc431d5c360209065f`.
It contains exactly 23 regular files, 5,167,184 uncompressed bytes:

- `state.sql`: standard-library SQLite `iterdump()` of one read-only snapshot,
  preserving schema42 `user_version`, all 81 tables, schema and rows, without
  database free pages/WAL files.
- `data/`: all 19 original public transcript/caption/summary files, byte-for-byte.
- `initial.json`: original all-table row counts/hashes and complete DATA manifest.
- `official-pricing-20261028.txt`: unchanged public price snapshot, SHA256
  `8b8c1f41835842f9f8dd316486ec2a3f34353d5e9d42eeb08a7b42876e5f1886`.
- `provenance.json`: test-only public/synthetic provenance. Original machine paths
  and setup-log narrative are omitted; no path to a live QA directory is followed.

`manifest.json` lists every member's exact size/SHA256. The fixture loads only after
checking the pinned archive hash, bounded file count/size, regular-file mode and
relative paths without traversal; extraction is exclusively into a fresh pytest
`tmp_path`. The trusted SQL dump is replayed there using standard SQLite. All fake
case tests actively refuse original absolute SOURCE access through file, directory
and SQLite entry points. The original 81-table/19-file/hash/4224-byte assertions stay.

The four public sources are:

- https://www.youtube.com/watch?v=0eMzc-WnBfQ
- https://www.youtube.com/watch?v=IwglW_hIL_g
- https://www.youtube.com/watch?v=QoXRfTb7ves
- https://www.youtube.com/watch?v=aircAruvnKk

Captions and their original attribution remain those public sources' content; this
fixture does not claim ownership or a new license over third-party captions. The
QoXRfTb7ves 18 timed cues are checked against the unchanged committed
`docs/validation/end-to-end-user-readiness/INTELLIGENCE_REAL_CORPUS_V2.json` oracle;
the original synthetic interest/profile, 2 complete canonical Evidence items and
verified-input hash remain exact. Existing non-case public/synthetic rows are kept
to exercise history preservation and full Backup/Restore rather than replacing
them with empty tables. Published summaries are existing isolated QA artifacts,
not claims of actual BigModel generation or quality.

Privacy inventory: only this authorized public/synthetic snapshot was read. No
native store, `.env`, credential, private owner input, live user QA, review approval,
once marker, request result, raw model reasoning, WAL, machine config or log is in
the archive. All DATA paths are `transcripts/...`; all preferences, cloud-consent
and config tables are empty. A scan of every archive member for credential-shaped
`sk-...`, private-key headers and Authorization/Bearer values found none. That scan
supplements the known source provenance; it does not turn unknown data into public.
No actual model/provider request was made to produce or test this fixture.
