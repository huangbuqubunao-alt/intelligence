# TASK-014：发布准备

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Owner role: PO + TL + QA
- Size: S
- Risk: Medium
- Depends on: TASK-013

## 目标

在不新增功能的前提下完成 V1 文档、安装运行、备份恢复、安全检查和发布门禁，形成明确的 Go/No-Go 决策。

## 范围

- 核对 README、配置示例、初始化、手动运行、doctor、launchd、备份/恢复和故障处理说明。
- 核对 PRD、System Design、实际 CLI、Schema 版本和验收报告一致。
- 由 PO/TL/QA/隐私 Reviewer 逐项签署发布清单。

## 范围外

- 不修复新发现缺陷；缺陷必须退回对应任务或新建范围明确的任务卡。
- 不新增依赖、重构、格式化全仓库或实现 V2 功能。
- 不自动部署、加载 launchd 或写入真实 Vault。

## 验收标准

- [ ] 从干净环境按 README 可安装并完成离线 smoke；备份/恢复说明在临时数据上验证。
- [ ] `docs/ACCEPTANCE_REPORT.md` 无未解释的 P0/P1 失败，所有剩余风险有负责人和处置决定。
- [ ] 复核 `.gitignore` 的 `data/`、`logs/` 边界：不得静默忽略实际使用的测试夹具、源码资源或文档目录；若届时仍存在误忽略风险，必须 No-Go 并退回范围明确的修复任务。
- [ ] 生成直接/传递依赖许可证清单并决定分发形态；特别复核 `yt-dlp[default]` 带入的 `mutagen` GPL-2.0-or-later 义务。未形成经 TL/发布负责人确认的兼容分发方案前不得发布二进制或捆绑依赖包。
- [ ] 若启用本地模型，复核 `mlx-whisper` 及其传递依赖许可证、MLX Community 转换模型
  card 缺失许可声明、Whisper 权重来源和缓存分发边界；若安装/调用 ffmpeg，确认其
  GPL 构建不被项目捆绑或重新分发。无明确处置不得把相关产物纳入发布物。
- [ ] 若启用 Ollama，复核程序版本、`qwen3:8b` 固定 digest、上游 Apache-2.0 证据和
  模型拉取/本机服务实际授权记录；不得把“本机 loopback”误记为无需供应链审查。
- [ ] 复核 TASK-008A/TASK-009A 的直接/传递依赖与分发边界：OpenAI SDK
  Apache-2.0、tiktoken MIT、Jinja2 BSD-3-Clause、MarkupSafe 及 OpenAI SDK 传递
  依赖；确认云端默认关闭、无真实密钥/响应进入发布物，固定 Jinja 模板不包含用户
  Vault 内容。
- [ ] 单独复核包内 `o200k_base.tiktoken` 的文件级来源、固定 SHA-256
  `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`、分发许可和
  NOTICE/归属要求；未形成书面结论前，不得把该资源纳入二进制或捆绑分发物。
- [ ] 复核正式 TASK-008 未在主进程导入 OpenAI SDK；隔离子进程环境为新建白名单且
  不继承 OpenAI/Azure/代理/凭据变量，密钥只在 SDK 导入握手后经匿名管道传入，并在
  异常、argv、文件、日志和进程退出路径中保持不可见。
- [ ] 四类 Reviewer 完成清单并给出 Go；任一红线项不满足则明确 No-Go，不得标记 V1 完成。

## 验证

- [ ] `python -m pytest`
- [ ] `ruff check . && mypy src`
- [ ] `python -m youtube_intel doctor`（只使用临时/示例配置）
- [ ] `git diff --check && git status --short`
- [ ] 人工检查：无密钥、无真实 Vault 内容、无未审批依赖/Schema/调度改动。

## 预计触达文件

- `README.md`
- `docs/OPERATIONS.md`
- `docs/ACCEPTANCE_REPORT.md`
- `docs/RELEASE_CHECKLIST.md`

## 交付证据

- Go/No-Go 记录和签署人。
- 干净环境 smoke、备份和恢复结果。
- 版本号、Schema 版本、已知限制和下一步任务链接。
- TASK-001 P2（未锚定 `data/`、`logs/`）的最终复核与处置记录。
- `yt-dlp` 全部直接/传递依赖的许可证证据、`mutagen` 分发处置与最终 Go/No-Go 结论。
- ADR-007 模型、ffmpeg、Ollama 与模型权重的来源/许可证/授权证据及最终处置。
- ADR-008/ADR-009 的 OpenAI/tiktoken/Jinja2/MarkupSafe 依赖清单、固定
  `o200k_base.tiktoken` 资源许可与哈希证据、SDK 隔离导入/匿名管道密钥门禁、云端
  隐私门禁和模板/Vault 分发边界。
