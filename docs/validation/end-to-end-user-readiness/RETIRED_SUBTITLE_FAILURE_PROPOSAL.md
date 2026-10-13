# 已知失败旧字幕请求的安全终止提案（隔离范围）

日期：2026-10-13，Asia/Shanghai。状态：用户已于 2026-10-13 明确批准该精确隔离整改与验收范围，开始独立实施；未正式采用。

## 真实问题和证据

正常公开视频先遇到 429，留下 subtitle.fetch/yt-dlp/provider_calls FAILED_RETRYABLE。后续选择/格式政策升级且正常重试取得真实字幕，旧 request_hash 不再被现行 Producer 重试；旧失败保留且无 owner/lease/response。但 Backup 对非终态 provider_calls 继续 fail-closed，永久阻塞。隔离 root DB 已读出两个旧 subtitle-selection-v1/subtitle-format-v1 请求（32ee6ce…、65f7db…），last_error_code RATE_LIMITED，owner/lease/response 都 null。另一个真正未结束的 Iwgl 视频 PENDING 也仍阻塞，必须先通过正常 Retry 结束；本提案不能忽略它。正式用户数据库未读取或改写。

## 请求的精确实现范围

只在独立候选新增一个正规的旧公共字幕失败终止方法，复用现有 provider_calls 表和 Backup protected write gate，无 Schema migration，无直接删除，也不修改 Backup readiness 判定。

事务内只允许：operation=subtitle.fetch/provider=yt-dlp/model=NULL，确切已退休 selection/format 版本组合；FAILED_RETRYABLE、已确认已知失败（初始范围只 RATE_LIMITED）、无响应产物、无 owner/lease、无未完成 dispatch/未知结果；系统无其他未完成 job、活动 Source Run/source check、未完提炼 checkpoint 或恢复请求。全局任一不确定条件则不执行该整理，继续阻塞。

安全终止结果记录为 FAILED_FINAL，保存原 request_hash、请求版本、错误代码/原始错误文字、计数、开始时间等历史信息，另加可读政策退休原因和完成时间。幂等；原始文件、Job、Content、Summary、Evidence、预算、授权、invocation 和真实调用记录完全保留。并发与新执行启动使用同一 SQLite 事务/现有保护 gate，不允许以过期结果覆盖重新领取的请求。不是把失败变成成功，不发起网络或模型调用。

挂接位置限定在普通已完成内容恢复/安全维护入口：只在所有真正未完成工作结束后尝试。旧版本一旦退休，当前 Producer 使用其新版本 identity；以后用户显式重试不复活已终止旧请求。未知版本、PENDING、云/模型调用、已有 response、活跃租约或未确定 dispatch 仍 fail-closed，不进行“清空失败记录”。

## 必需验证

先建立旧429→正常新政策成功→仍被旧ledger阻塞的回归；安全终止后正常 Backup readiness 开放。重复操作/重启/BackupRestore记录一致。并发领取/开始与终止只允许一方获得所有权。其他任务/未知状态/当前版本/未知版本/非字幕云调用/response不为空均不能错误终止或放开备份。保留旧错误、原 artifact/Evidence/Job，不删表、不改资格门禁。独立审查和真实 GUI BackupRestore后才能纳入最后发布候选。

## 权限与风险

这增加 invocation/provider ledger 生命周期的持久化边界，属于用户全局 AGENTS.md “security-sensitive code”须先获得具体批准；此前字幕补全批准只覆盖新 repair child，不应推定包含旧失败请求终止。因此尚未实现。只授权隔离实现与验收，不授权正式数据变更或 main采用。其他已批准字幕/声学/模型及界面验收继续进行。

## 明确批准记录

用户对该具体问题回复：“批准该精确隔离整改与验收范围”。仅本提案的隔离 Producer 终止/并发/恢复测试获授权；正式 main/配置/数据采用仍需最终具体批准。
