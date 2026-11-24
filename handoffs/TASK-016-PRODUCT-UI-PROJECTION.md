# PRODUCT UI READ PROJECTION — IMPLEMENTATION PACKET 1

## 元数据

- Task: `PRODUCT UI READ PROJECTION — IMPLEMENTATION PACKET 1`
- Role: `Implementer`
- Base branch/commit: `main@efa748a0e3c52cc7672c6b819ab67646e03e9e1e`
- Worktree: `/Users/developer/Documents/yia-worktrees/task-016c-main-integration`
- Branch: `main`

## 目标与范围

- 任务目标：以既有 Artifact、VideoRecord、Job/Attempt、ReportRecord、SourceVideoLink 与 AutomationRun authority 完成安全产品读投影。
- 实际修改：Local API composite DTO、SourceVideoLink 单查询 reader、前端 Tab/Drawer 消费以及 focused API/UI tests。
- 明确未做：未新增 schema、依赖、NoteRef persistence、Note V2/Weekly V2 authority、Provider/Credential/Scheduler 语义、真实 Vault 或网络调用。

## 复用决策

- `DIRECT`：既有 `TRANSCRIPT_CANONICAL` index + hash-bound DATA artifact、`VideoRecord`、`JobRecord`/`JobAttemptRecord`、`ReportRecord`、`SourceVideoLink`、`AutomationRunRecord` 与 `AuthoritativeScoringReader`。
- 未引入第三方代码或依赖；无许可证新增事项。

## 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| 安全 transcript / note / lifecycle / weekly / source projections | PASS | `uv run pytest tests/unit/test_local_api.py -q` → 14 passed |
| 前端消费 | PASS | `npm run typecheck && npm test && npm run build` → typecheck、6 UI tests、build 通过 |
| trust regression | PASS | scoring/verified-note/weekly/deep-analysis/dispatch selection → 93 passed |
| Python 全回归 | PASS | 全部 tests 分片：1,963 passed, 1 skipped |
| 类型与 lint | PASS | `uv run mypy src`; `uv run ruff check .` |
| package | PASS | `uv lock --check --offline`; `uv build --offline`; wheel/sdist listings inspected |
| scanner | EXPECTED NONZERO | `bash scripts/security_scan.sh` → exit 1, 11 accepted intentional fixtures, 0 new findings |

## Diff 复核

- Controller 只将验证后的 route 分派至 safe DTO helpers；没有 raw DB dump。
- transcript reader 只接受 indexed canonical DATA artifact、受限相对路径、无 symlink、SHA-256 和 UTF-8 验证；DTO 从不暴露 storage path/root。
- Note V1 是 `NOTE_REF_NOT_PERSISTED`，没有 filename inference；Note V2 和 Weekly V2 均为 `UNAVAILABLE`。
- `AMBIGUOUS` 保持原状态并呈现禁止自动重试的固定解释。
- Source recent videos 使用单个 `source_video_links JOIN videos` 查询；无 title matching 或 ownership 重定义。

## 实现者结论

- 建议状态：`IN_REVIEW`
- `DECISION NEEDED`：`None`
