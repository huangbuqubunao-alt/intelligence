# TASK-014B11 — Pre-merge Credential-shape Leak Triage Scout（只读）

你是 TASK-014B11 的全新 Codex Leak Triage Scout。目标仅是定位并分类 Product Integrator
预合并综合静态泄漏扫描 `exit 32` 的“凭据类名称后跟赋值”命中来源；不得修复、放宽门禁、
重新运行 Product Integrator 或批准合并。本包本身不启动 Scout。

## 必读资料与固定对象

开始前完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、
`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、ADR-021、
`tasks/TASK-014-release-readiness.md`、`tasks/TASK-014B11-safe-directory-contract-diagnostics.md`、
原 Product Integrator 包、本包及 B11 handoff。若边界冲突，立即停止并报告。

```text
Task: TASK-014B11 — pre-merge credential-shape leak triage
Role: Read-only Leak Triage Scout
Agent: Codex
Control-plane parent/base: main@a92e321216f418e0add6f01f7d1f300dcce11ea6
Accepted source worktree: /Users/hua/Documents/yia-worktrees/task-014b11-safe-directory-contract-diagnostics
Accepted source branch: codex/task-014b11-safe-directory-contract-diagnostics
Accepted source HEAD: f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d
Product base: 80aff83fc033a8bd2950108cad2e34feea5d396f
Inspected range: 80aff83fc033a8bd2950108cad2e34feea5d396f...f57b21ce8a9369e9f11e4dab200f5d3dc9fa162d
Failed gate: Product Integrator combined static leak scan, exit 32
Reuse decision: DIRECT — Git object inspection, tracked Markdown/source text and SHA-256 only; no dependency or external tool
```

- 开始前只读核验 main 包含本授权、source 分支/HEAD/工作树/暂存区固定且干净，并确认
  accepted source 尚未进入 main。任一不符立即停止。
- 固定事实：此前 Product Integrator 的 Git 前置、lock check、locked offline sync、三个生产链
  tests、focused、full pytest、mypy、Ruff、CLI help、offline build 与三组 `git diff --check`
  已通过，但综合静态泄漏扫描以 `exit 32` 停止；merge 未执行。Scout 不得把该扫描改写为通过，
  也不得复用其他通过项批准合并。

## 唯一允许范围与一次 locator

只允许检查上述固定 range 的以下完整 B11 五路径 Diff：

1. `src/youtube_intel/providers/subtitles.py`
2. `src/youtube_intel/public_subtitle_smoke.py`
3. `tests/integration/test_subtitle_provider.py`
4. `tests/integration/test_public_subtitle_smoke.py`
5. `handoffs/TASK-014.md`

允许重新执行一次专用、只读、最小化 locator。它只能查找失败报告所述
`credential-name-followed-by-assignment` 规则类别，不得运行原综合扫描、扩大规则、修改规则或把
locator 结果当作门禁通过。locator 对每个命中只能输出：

- 仓库相对文件路径；
- accepted source 中的行号；
- 固定规则类别 `credential-name-followed-by-assignment`；
- 匹配行原始 tracked bytes（不含行结束符）的 SHA-256；
- `added_line=true|false`，表示该行是否属于固定 range 的新增行。

允许 Scout 在本地只读查看匹配内容以完成分类，但 locator、终端输出、聊天报告和任何文档均不得
回显匹配值、整行内容、前后文、异常原文、URL、视频 ID 值、token、secret、Cookie、payload、
路径值、用户数据或其他潜在敏感材料。命中计数与各条脱敏元数据必须可相互核对；无法安全定位或
分类时使用 `unknown` 并保持阻断。

## 固定分类与处置建议

每个命中必须且只能归入以下一类：

1. `confirmed-secret-or-credential`：真实或无法排除的凭据材料。建议立即保持 `REJECT`/阻断，
   并说明是否需要凭据轮换或独立安全响应；不得显示值。
2. `synthetic-test-sentinel`：测试中的合成凭据形状。建议以最小测试材料 Correction 关闭；不得
   放宽扫描器。
3. `scanner-self-match`：泄漏扫描规则、断言或安全检查本身触发。提出最小、精确、只针对该已证明
   自匹配的门禁处置；不得建立通用忽略、删除检查或降低覆盖。
4. `documentation-example`：文档/handoff 中的示例或报告文字。建议改写为非凭据赋值形状；不得
   放宽扫描器。
5. `unknown`：无法安全判断。保持阻断。

后续建议必须给出最小任务及精确允许路径，并明确：

- 只有全部命中都能安全证明为无需修改 accepted source 的 `scanner-self-match`，才可建议主控继续
  使用现有 accepted source；仍须新的控制面门禁处置与重新授权，Scout 自身不能恢复 Integrator。
- 任一 `confirmed-secret-or-credential`、`synthetic-test-sentinel`、`documentation-example`，或任何
  需要改变五路径 tracked 内容的处置，都必须建议 Correction 2；其范围只能是实际命中文件与
  必要 handoff 的最小子集，并重新接受独立审查和验收。
- 任一 `unknown` 保持阻断，不得建议合并。

## 聊天回传格式

只向主控对话回传一份脱敏报告，不写仓库：

```text
Task: TASK-014B11 leak triage
Observed main/source: <SHA / clean or blocked>
Fixed range and paths: <pass or blocked>
Locator runs: 1 | 0 with reason
Hit count: <integer>
Hits:
- path: <repository-relative path>
  line: <integer>
  rule: credential-name-followed-by-assignment
  line_sha256: <64 lowercase hex>
  added_line: true | false
  classification: confirmed-secret-or-credential | synthetic-test-sentinel | scanner-self-match | documentation-example | unknown
Real credential risk: yes | no | unknown
Minimum next task and allowed scope: <exact task/scope>
Accepted-source disposition: reuse-current-source | correction-2-required | blocked-unknown
Merge authorization: NOT GRANTED
Decision needed: None | <details>
```

不得自行给出 `APPROVE`、恢复 merge、修改 TASK-014B11 状态或把 locator 结论写成产品/真实 smoke/
发布通过。

## 绝对禁止

- 禁止运行原综合泄漏扫描作为重试；禁止 `uv`、Python/import、pytest、mypy、Ruff、build、任何
  产品 CLI、网络、YouTube、真实 smoke、认证、Cookie、媒体、ffmpeg、Vault、模型、OpenAI、云端
  或其他真实资源。
- 禁止修改、写入、暂存、提交、合并、cherry-pick、rebase、reset、push、清理 source 或创建
  Correction；禁止改变任务状态、扫描规则或 Product Integrator 包。
- 禁止创建 `.codebase-memory`、`.codegraph`、索引、缓存、报告文件或其他仓库/工作树工件。
- TASK-014B11 保持 `ACCEPTED`；TASK-014 保持 `IN_PROGRESS / No-Go`。Scout 结论不是合并批准、
  真实凭据安全证明、真实兼容性证明、真实 smoke、正文可读或发行批准。
