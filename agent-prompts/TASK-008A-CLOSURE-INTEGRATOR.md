# TASK-008A 收口同步 — Status Integrator

你是全新的 Codex Status Integrator。你只提交主控准备的 TASK-008A 收口控制面；不得实现、审查、合并、rebase、push、清理 source/worktree，且不得运行 `uv`、pytest、mypy、Ruff、build、网络、数据库或产品命令。

## 固定事实

- 工作目录/分支：`/Users/hua/Documents/youtubek agent` / `main`
- Required base 与 TASK-008A merge：`64a9c41683bb559b27bebb784fcff4fbff644a18`
- Merge parents（顺序固定）：`d00841802ef375170542e7458ecba0504b6fd182`、`7a8239f3da02fa204b63702677fae5f669fb99c0`
- Accepted source：`codex/task-008a-cloud-analysis-shared-contracts@7a8239f3da02fa204b63702677fae5f669fb99c0`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-008a`
- 身份必须是 `Mozhu <huangbuqubunao@gmail.com>` 且 `user.useConfigOnly=true`。

## 唯一允许提交范围

仅以下五个主控预写 Markdown 文件；内容与 SHA-256 在检查期间必须稳定：

1. `agent-prompts/TASK-008A-CLOSURE-INTEGRATOR.md`
2. `docs/PROJECT_STATUS.md`
3. `handoffs/TASK-008A.md`
4. `tasks/README.md`
5. `tasks/TASK-008A-cloud-analysis-shared-contracts.md`

初始工作树只能有上述五个未提交变更，暂存区必须为空。任何额外/并发变更、哈希变化、身份、父链、范围或内容冲突，均立即 `BLOCKED`，不得覆盖、重新生成、取消暂存或清理。

## 必须核验

1. `64a9...` 是双父 merge，父顺序精确为 `d008...` 后 `7a823...`；accepted source 是 merge 祖先且 source worktree 干净。
2. `git diff --name-only 64a9^1 64a9` 精确为八个批准路径：`config/settings.example.yaml`、`handoffs/TASK-008A.md`、`pyproject.toml`、`src/youtube_intel/config.py`、`src/youtube_intel/domain.py`、`src/youtube_intel/resources/o200k_base.tiktoken`、`tests/unit/test_contracts.py`、`uv.lock`。
3. BPE 资源为 `3,613,922` bytes，SHA-256=`446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`。
4. 既有整合证据完整：locked offline sync、contracts `72 passed`、全量 `324 passed`、mypy、Ruff、CLI、offline build、sdist/wheel migration 与 BPE 核验均 PASS，无 P0–P3。
5. 五个控制面必须一致将 TASK-008A 关闭为 `DONE`，记录 merge SHA 和 BPE NOTICE/license 的 TASK-014 release gate；不得改写历史审查结论。
6. TASK-009A、TASK-008、TASK-009 均保持 `BLOCKED/UNASSIGNED`；不得创建其分支/worktree/分配包。

执行身份/分支/HEAD/索引、上述 merge/source/range/BPE、五文件双轮 SHA-256、LF-at-EOF、尾随空白、`git diff --check`、暂存范围与 `git diff --cached --check`；不得运行产品命令。

全通过后只创建一个单父提交：

```text
docs: close TASK-008A after integration
```

回传 `Task/Role/Base/Head/identity/精确文件范围/收口条件/最终状态/Post-commit status/Verdict/remaining risks`。
