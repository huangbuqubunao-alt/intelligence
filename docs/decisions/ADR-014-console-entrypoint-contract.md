# ADR-014：正式 console entry 打包契约

## 状态

Accepted

## 日期

2026-07-27

## 背景

`youtube_intel.cli:main` 已实现并由 `python -m youtube_intel` 使用，但已安装项目没有正式的
`youtube-intel` console command。TASK-014 Phase B-1 的入口缺失阻断证据 `4a349055…` 不能被视为
smoke 成功或重试授权；它只说明发布 QA 需要一个可安装、可验证的正式入口。直接添加新包装脚本、独立
composition root 或第二套参数解析会扩大既有 CLI/安全边界，不能接受。

## 决策

- 在 `[project.scripts]` 中仅声明 `youtube-intel = "youtube_intel.cli:main"`。
- 保留 `python -m youtube_intel` 与既有 `cli.main` 参数、退出码、默认 fail-closed、`smoke-public-subtitles`
  受限入口和所有资源边界，不改变业务编排或 Adapter 调用图。
- TASK-014B2 只可更新最小打包元数据；如 `uv lock --check` 确有需要，可重新生成 `uv.lock`，但锁定包集合、
  名称、版本、来源和依赖关系不得新增、升级或删除。
- 离线验证只确认安装后的 console entry 和模块入口都能显示帮助并映射到同一 CLI 主入口；不得调用
  YouTube、真实 smoke、Vault、凭据、模型或其他真实资源。

## 后果

- 用户和发布 QA 获得稳定的 `youtube-intel` 命令，而不引入第二套 CLI 行为。
- B-1 的 `4a349055…` 阻断 evidence 保持在其 source，绝不合并、绝不写成通过或据此自行发起真实 smoke。
- 这不是发布批准；TASK-014 仍受 mutagen GPL、BPE 文件级归属/NOTICE、真实 smoke/Vault、at-most-once
  风险签署和最终 PO/TL/QA Go-No-Go 门禁约束。

## 考虑过的方案

### 新建包装模块或自定义 shell 脚本

拒绝。会复制或绕过既有 CLI 的参数解析、退出码和受限 smoke 安全边界。

### 继续只支持 `python -m youtube_intel`

拒绝。不能满足已安装发行物的正式命令需求，也不能关闭入口缺失这一发布 QA 前置条件。
