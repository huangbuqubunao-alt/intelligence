# TASK-008A — Product Integrator

你是全新的 Codex Product Integrator。你只整合已经独立审查并被主控 `ACCEPTED` 的
TASK-008A source；不得实现、修复、重构或改变审核过的产品内容。若任何门禁、范围、
测试、构建或安全检查失败，立即停止并报告 `BLOCKED`，不得自行修复、amend、rebase、
cherry-pick、reset、清理 source 或选择其他 SHA。

## 固定基线与对象

- Main repository：`/Users/developer/Documents/youtubek agent`
- Acceptance anchor：`aa134f43af57e6f6bdc7455b56c59ac97ee342e7`
- Execution base：动态运行
  `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008A-INTEGRATOR.md`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-008a`
- Source branch：`codex/task-008a-cloud-analysis-shared-contracts`
- Accepted source head：`7a8239f3da02fa204b63702677fae5f669fb99c0`
- Correction implementation：`d95745fd04b115369a9fd70362cd735d1eb70917`
- Original task base：`82d1fd7c7f2f82e77df0518e63755bad0bf240f2`
- Required identity：`Mozhu <maintainer@example.invalid>`；
  `user.useConfigOnly=true`

开始时 main 必须在动态 execution base，且其唯一父为 Acceptance anchor；main/source
均干净，暂存区为空。TASK-008A 必须为 `ACCEPTED`，source 必须位于 accepted head、
分支正确且干净。accepted head 的唯一父为 Correction implementation，且只修改
`handoffs/TASK-008A.md`。任一条件不符立即 `BLOCKED`。

## 预合并范围与批准边界

相对 original task base 的完整产品范围只能精确为：

1. `config/settings.example.yaml`
2. `handoffs/TASK-008A.md`
3. `pyproject.toml`
4. `src/youtube_intel/config.py`
5. `src/youtube_intel/domain.py`
6. `src/youtube_intel/resources/o200k_base.tiktoken`
7. `tests/unit/test_contracts.py`
8. `uv.lock`

还必须确认：

- Correction 相对 first review evidence 只改 `domain.py`、`config.py`、contracts、
  resource 和 handoff；
- `pyproject.toml`/`uv.lock` 相对 Correction 前 implementation blob 不变；
- resource source SHA-256 和大小分别为
  `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d` / `3,613,922`；
- 无 Provider、`analysis.py`、Prompt、Schema/migration、`state.py`、
  `complete_stage`、CLI、任务/ADR、真实密钥、API 响应、cache、媒体或模型文件；
- BPE file-level NOTICE/许可证仅记录为 TASK-014 发布风险，不得在本轮推断已解决。

真实 OpenAI/API、密钥读取、付费调用、cloud token-count、Vault/用户内容、媒体、模型
和所有网络均未授权。所有 `uv`/build 检查必须离线；cache 缺失即 `BLOCKED`，不得联网。

## 合并与必须检查

1. 在 main 使用 `git merge --no-ff --no-commit` 合并 accepted source；发生冲突或范围
   漂移立即停止，不手改冲突内容。
2. 在暂存合并态先运行：

```bash
git diff --cached --check
git diff --cached --name-status
uv lock --check
uv sync --locked --offline
uv run python -m pytest tests/unit/test_contracts.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
```

3. 验证实际 focused 计数 `72 passed`、全量 `324 passed`；sdist/wheel 都包含
   `youtube_intel/migrations/001_initial.sql` 与 BPE resource，解包后资源大小/哈希均
   精确匹配。
4. 检查 staged 及 first-parent 产品 Diff 只含上述八路径，运行敏感字面量扫描；不把
   BPE 哈希或合成测试哨兵误报为秘密。
5. 全部通过后创建 merge commit，保留默认 merge message 或使用：

```text
merge: integrate TASK-008A cloud analysis shared contracts
```

6. 提交后确认 merge 有且仅有两个父提交，第一父为 execution base、第二父为 accepted
   source；accepted source 是 main 祖先；main/source 均干净。

只可清理本轮生成且被忽略的 `dist/`，不得删除 BPE source resource、source worktree、
分支或其他 Agent 文件。不得 push。

## 交付状态与回传

合并后 TASK-008A 必须仍为 `ACCEPTED`，不得改为 `DONE`，不得解锁或分配 TASK-009A、
TASK-008、TASK-009。关闭状态由后续独立 Status Integrator 同步。

```text
Task: TASK-008A
Role: Product Integrator
Acceptance/execution base:
Source head:
Merge commit:
Merge parents:
Pre-merge scope:
Checks:
Build/resource evidence:
Post-merge task status:
Post-merge main/source status:
Git identity:
Unexpected files:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
