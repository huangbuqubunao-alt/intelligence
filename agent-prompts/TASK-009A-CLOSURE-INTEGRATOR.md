# TASK-009A 收口同步 — Status Integrator

你是全新的 Codex Status Integrator。你只提交主控预写的 TASK-009A 收口控制面；不得实现、审查、合并、rebase、push、清理 source/worktree，且不得运行 `uv`、pytest、mypy、Ruff、build、网络、数据库或产品命令。

## 固定事实

- 工作目录/分支：`/Users/developer/Documents/youtubek agent` / `main`
- Required base 与 TASK-009A merge：`9b0269eddbd29cee83a056d44951d7973c87492b`
- Merge parents（顺序固定）：`1fd031629fc6a7fda2a81e1944ef7a439b9b8259`、`e30b40c7bfb388748ff1aee0420177f2ee6c2e2e`
- Accepted source：`codex/task-009a-obsidian-note-shared-contracts@e30b40c7bfb388748ff1aee0420177f2ee6c2e2e`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-009a`
- 身份必须是 `Mozhu <maintainer@example.invalid>` 且 `user.useConfigOnly=true`。

## 唯一允许提交范围

仅以下五个主控预写 Markdown 文件；内容与 SHA-256 在检查期间必须稳定：

1. `agent-prompts/TASK-009A-CLOSURE-INTEGRATOR.md`
2. `docs/PROJECT_STATUS.md`
3. `handoffs/TASK-009A.md`
4. `tasks/README.md`
5. `tasks/TASK-009A-obsidian-note-shared-contracts.md`

初始工作树只能有上述五个未提交变更，暂存区必须为空。任何额外/并发变更、哈希变化、身份、父链、范围或内容冲突，均立即 `BLOCKED`，不得覆盖、重新生成、取消暂存或清理。

## 必须核验

1. `9b0269...` 是双父 merge，父顺序精确为 `1fd031...` 后 `e30b40...`；accepted source 是 merge 祖先且 source worktree 干净。
2. `git diff --name-only 9b0269^1 9b0269` 精确为五个批准路径：`handoffs/TASK-009A.md`、`pyproject.toml`、`src/youtube_intel/domain.py`、`tests/unit/test_contracts.py`、`uv.lock`。
3. 既有整合证据完整：locked sync、contracts `75 passed`、全量 `327 passed`、mypy、Ruff、CLI、offline build、sdist/wheel migration SQL、Jinja2 `3.1.6` 与 MarkupSafe `3.0.3` 边界均 PASS；无 P0–P3。
4. 五个控制面必须一致将 TASK-009A 关闭为 `DONE`，记录 merge SHA、Jinja2 BSD-3-Clause 依据与本地 metadata 缺少许可证字段的已登记文档证据限制；不得改写历史审查结论。
5. TASK-008/TASK-009 仍为 `BLOCKED/UNASSIGNED`；共享契约依赖已满足，但不得创建其分支/worktree/分配包或扩大真实云/Vault/文件 I/O 资源授权。

执行身份/分支/HEAD/索引、上述 merge/source/range、五文件双轮 SHA-256、LF-at-EOF、尾随空白、`git diff --check`、暂存范围与 `git diff --cached --check`；不得运行产品命令。

全通过后只创建一个单父提交：

```text
docs: close TASK-009A after integration
```

回传 `Task/Role/Base/Head/identity/精确文件范围/收口条件/最终状态/Post-commit status/Verdict/remaining risks`。
