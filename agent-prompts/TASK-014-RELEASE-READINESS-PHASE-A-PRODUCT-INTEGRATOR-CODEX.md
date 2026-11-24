# TASK-014 Phase A — Codex Product Integrator

你是全新的 Codex Product Integrator。只整合已接受的 TASK-014 Phase A source；不得开发、修复、修改 source、重写历史、push 或清理任何 worktree。任一身份、范围、文档门禁或合并冲突失败都必须停止并报告，不得在整合中补救。

## 动态授权与固定对象

- 本授权文件在 main 的最新提交必须是本次 Product Integrator 授权提交，且其唯一父提交必须为
  `4589b1af36ac68e5451cbeed7062ab0c8f212f42`。执行 base 是该授权提交本身；不得从其他基线整合。
- 唯一 accepted source：`/Users/developer/Documents/yia-worktrees/task-014-release-readiness-phase-a`，分支
  `codex/task-014-release-readiness-phase-a`，HEAD 固定为 accepted reviewer evidence
  `88f1b36fdef75146315e91f93b71c36463132ffb`。
- `88f1b36fdef75146315e91f93b71c36463132ffb` 的唯一父提交必须为实现 commit
  `8c35cd0a2c764a6ed9483ea6c8377c8f6ca0ab59`；source 工作树必须干净。
- Phase A 的审查基线为 `d0d136a4754a97954f64f1ca39b87837e639decc`。`d0d136a...88f1b36...` 的完整 Diff
  必须严格为本包列出的七条路径；任何其他路径、依赖、锁文件、Schema/migration 或产品代码变化均阻断整合。
- 当前 TASK-014 继续为 `IN_PROGRESS / No-Go`。本包不授权发布、法律结论、真实 smoke、风险接受或最终 Go/No-Go。

```text
Task: TASK-014 Phase A — Release readiness materials and risk disclosure
Role: Product Integrator
Agent: Codex
Execution base: dynamic main authorization commit (sole parent 4589b1a...)
Accepted source: codex/task-014-release-readiness-phase-a@88f1b36...
Merge: git merge --no-ff 88f1b36fdef75146315e91f93b71c36463132ffb
Reuse decision: DIRECT — 仅整合已审查的项目 Markdown 与 .gitignore 根目录锚定修正；不新增依赖或第三方材料
```

## 唯一允许范围

被合并的 source first-parent Diff 只能包含：

1. `.gitignore`
2. `README.md`
3. `docs/SBOM.md`
4. `docs/THIRD_PARTY_NOTICES.md`
5. `docs/RELEASE_CHECKLIST.md`
6. `docs/SMOKE_AUTHORIZATION_MATRIX.md`
7. `handoffs/TASK-014.md`

不得修改主线控制面、任务状态、产品代码、测试、配置、依赖、锁文件、Schema/migration、项目自身 `LICENSE`，也不得修改 source handoff 或 source 的任何文件。

## 整合步骤与必须核验

只允许 Git/文档门禁。合并前确认 main 与 source 都干净、branch/HEAD/父链精确匹配，确认
`d0d136a...88f1b36...` 的文件范围和 `git diff --check` 通过。随后只执行无冲突的 `--no-ff` 合并；出现冲突立即停止，不自行编辑解决。

合并后必须记录并核验：

1. 新 merge commit 的双父顺序：第一父为动态 execution base，第二父为
   `88f1b36fdef75146315e91f93b71c36463132ffb`；accepted source 必须成为 merge 祖先。
2. merge 的 first-parent Diff 严格为上述七条路径，且 `git diff --check` 通过。
3. `README.md`、`docs/SBOM.md`、`docs/THIRD_PARTY_NOTICES.md`、`docs/RELEASE_CHECKLIST.md`、
   `docs/SMOKE_AUTHORIZATION_MATRIX.md` 与 `handoffs/TASK-014.md` 均进入 main；逐份进行 Markdown/文本核验。
4. `.gitignore` 的运行目录规则只为根目录锚定的 `/data/` 与 `/logs/`，不存在未锚定的 `data/` 或 `logs/` 忽略规则。
5. README、SBOM、NOTICE、发布检查表与 smoke 矩阵继续明确：`mutagen` GPL 分发结论、
   `o200k_base.tiktoken` 文件级归属/NOTICE、真实 smoke、真实 Vault 边界、at-most-once best-effort 风险签署和
   最终 PO/TL/QA Go-No-Go 均为未关闭 No-Go 门禁；不得把资料整合写成发布批准、法律结论、真实 smoke 或严格 exactly-once。

## 禁止项

- 不运行 uv、pytest、mypy、Ruff、build、Python/import、产品 CLI、网络、真实资源、真实 smoke、Vault 或凭据操作。
- 不访问、修改或清理 source；不启动 Reviewer 或其他 Worker；不 push、rebase、reset、cherry-pick 或删除文件。
- 不把 TASK-014 标为 `DONE`，不创建项目 LICENSE，不作许可证法律结论。

## 回传格式

```text
Task: TASK-014 Phase A Product Integrator
Execution base / merge: <authorization SHA> -> <merge SHA>
Source: codex/task-014-release-readiness-phase-a@88f1b36...
Parents / ancestor: <first parent>, 88f1b36... / PASS|BLOCKED
First-parent scope: <exact seven paths> / PASS|BLOCKED
Document and .gitignore gates: PASS|BLOCKED
Commands: Git/Markdown inspection and --no-ff merge only
Task state: TASK-014=IN_PROGRESS / No-Go
Remaining gates: mutagen GPL; BPE ownership/NOTICE; real smoke; real Vault; at-most-once sign-off; final PO/TL/QA Go-No-Go
Decision needed: None | details
```
