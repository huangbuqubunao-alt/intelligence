# READINESS-03-SOURCE-CONTEXT 交接报告

## 元数据

- Role: Implementer; agent `/root/source_context`.
- Base: `b861de3d96ad14f72ecad2a824f5f7dac07e42e2`.
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-source-context`.
- Branch: `codex/task-readiness-source-context`.
- Date: 2026-10-13.
- Reviewer: `/root/intel_bounded_review`, awaiting independent review.
- Implementation commit: supplied with the final handoff message; no self-merge.

## 目标、范围与复用

没有自定义 display_name 的 VIDEO_URL 来源已经持久化真实 channel_name，
但 verified Intelligence 输入只读 display_name，因而丢失来源名。修复后使用
`source.display_name or video.channel_name`，将同一个有效值放入 verified input
和 semantic payload。没有名称时继续 None；不猜测、不修改持久化历史。

实际业务代码仅 `_compose_verified_input` 的三处；另增独立集成测试、限定任务卡
和本交接。无 prompt 调参、parser、资格 receipt、schema、依赖、正式配置或数据
修改。用户已批准本轮隔离洞察输出/证据绑定整改，准确范围参见主控 worktree 的
`docs/validation/end-to-end-user-readiness/MODEL_REMEDIATION_PROPOSAL.md`。

DIRECT：现有 SQLiteStateRepository、exact Evidence resolver、semantic hashing、
reservation identity、标准库与已有 pytest。实现是项目的现有上下文投影修正，未复制
外部代码，无新增依赖或许可证义务。REJECT：推测说话人、caller 自由原文、重写旧
来源字段、手动翻转资格。PRD §7.2/§9.3 和 System Design §19 的来源/输入身份规则
继续生效。

## 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| VIDEO_URL 无 display_name 时保留已有频道名称 | PASS | 初始 RED 返回 None，修复后 Fixture channel；原 source row 不变 |
| 重启保留输入与封存身份 | PASS | 新 repository/service 重构相同 command/VerifiedInput；零调用 |
| 名称仅作为 source data | PASS | Ollama 固定 transport 测试的 user context 有名，system 无名字；生产资格仍 false |
| 显式来源名称优先 | PASS | 后续 metadata 改名不改变已有显式名的 verified input/hash |
| 元数据 fallback 改名使旧 reservation 失败关闭 | PASS | semantic hash 改变；旧记录不可重构，记录和 invocation_count 不变 |
| 名称都缺失时不推测 | PASS | 即使有 video_title 仍返回 None |

以上为离线 fixture 合同验证，**不是真实模型资格或普通用户端到端验收**。
名称完善不能证明模型会准确引用来源或满足语义标准。

## 检查结果

| 命令 | 结果 |
|---|---|
| Python py_compile：修改业务文件与新测试 | PASS |
| pytest：source context / wire branches / personalized distillation / reservation / dispatch / Ollama / Moonshot / OpenAI 8 文件 | PASS，229 passed，82.61 s |
| Ruff：distillation.py + 新测试 | PASS |
| Strict mypy：src/youtube_intel/distillation.py | PASS，1 source file |
| git diff --check | PASS |

初始新测试 3 failed / 2 passed：两个失败直接复现遗漏名称；第三个是测试 wire
fixture 缺少必需 response.model，已补齐 qwen3:8b，不放宽生产响应验证。第一次
修复后 4 passed / 1 failed：生产端确实拒绝旧身份，但新测试匹配了错误的英文
错误消息；阅读现有异常后改为精确 `not persistently reconstructible`，仍要求
StateStoreError，未放宽失败关闭断言。

## Diff、风险与待审查

- 无任务范围外业务修改、格式噪声、生成产物或锁文件变动。
- 测试数据库均为 pytest tmp_path；未访问正式 owner DB、云服务或本地模型。
- 只读复用既有 .venv 的 worktree symlink 为忽略文件，没有依赖安装。
- 历史 NULL 来源名的封存输入与新 fallback 语义不同；原 reservation 不会静默升级，
  会按既有身份门禁失败关闭。主控必须使用新隔离 reservation/重新资格验证，不可
  沿用旧 receipt；没有删除或改写旧历史。
- 本次未运行仓库全量后端/前端或 macOS GUI：主控整合后按原完整门禁执行。
- 无 `DECISION NEEDED`；建议进入 IN_REVIEW，不能自行标记 DONE。

## Reviewer 与主控验收

待独立审查。没有主控 ACCEPT，没有 main 整合或正式采用。
