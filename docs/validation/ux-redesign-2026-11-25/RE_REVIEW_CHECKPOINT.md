# 独立二次复审整改断点检查点（Re-Review Checkpoint）

> 主线任务书：`docs/validation/ux-redesign-2026-11-25/06_INDEPENDENT_RE_REVIEW_AND_MERGE_GATES.md`（`2e026d36`）
> 当前分支：`antigravity/remediation-20261125`（从 `origin/main@d1b58f731adc4185fe78cc5538e9e211b8a0e211` 线性推进）
> 上轮代码基准：`913b2c06030caf7fa9a69e5f07737cc5269e57f2`｜上轮交付基准：`9a8444e61858a73eaad1a0c05d8bf9093756fede`
> **最终代码与 CI 验证 SHA（`VERIFIED_CODE_SHA`）**：`84765be841c889ea3152590874be846ff4592518`
> **Draft PR**：[#50](https://github.com/huangbuqubunao-alt/intelligence/pull/50)（`isDraft: true`）
> **CI Run**：[`45650081266`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45650081266) — **`success`（14 / 14 Jobs 全部通过）**
> **当前阶段**：**所有代码批次回归、Gate E2 实机截图、14/14 远端 CI 与 `07_RE_REVIEW_REMEDIATION_ACCEPTANCE_REPORT.md` 已完成 → R1 处于 HOLD（等待独立 Reviewer 第三轮复审与用户最终批准）**

## 1. Phase 0–3 完成态核验表

| 编号 | 阶段状态 | 复现与最终验证摘要 |
|---|---|---|
| `P1-R01` | **FIXED & VERIFIED** | `b699cba9` + `fc252210`：原子 `Decimal` 类型事实与句内主客体/趋势/币种/单位/编号绑定、`G01–G12`、混杂句按逗号子句剔除、长段摘录居中、冷加载片段保持与双语综合放行、`history/restore/ZIP` 全出口一致。 |
| `P1-R02` | **FIXED & VERIFIED** | `d2daab30`：`update_config`/`disconnect` 事务内保留有效 `circuit_open_until`，`_finalize_attempt_slot` 取 `max()`，`11 passed`。 |
| `P1-R03` | **FIXED & VERIFIED** | `222235f1`：`youtube_auth_video_grants` 默认 10 分钟单视频单次授权，显式勾选全局持续模式，拆分保存与重试失败状态并支持原地撤销。 |
| `P2-R01` | **FIXED & VERIFIED** | `7ba77c6c`：>20 位 ASCII Range 有界解析拦截，避免 Python `int()` 超限崩溃。 |
| `P2-R02` | **FIXED & VERIFIED** | `7ba77c6c`：`HEAD` 按 RFC 9110 §14.2 忽略 `Range` 返回完整元数据及 0 正文（含裸 TCP Socket `b""` 测试）。 |
| `P2-R03` | **FIXED & VERIFIED** | `d2daab30`：旧 Keychain 读取重滤、清除任意注释行、浏览器 `cookiejar` 原地白名单过滤。 |
| `P2-R04` | **FIXED & VERIFIED** | `222235f1`：取消/完成/切换模式/范围/视频/卸载均严格清空 `cookiesText` 且取消零授权请求。 |
| `P2-R05` | **FIXED & VERIFIED** | `6820f941`：模态抽屉开启态设置背景兄弟 `inert`、`focusin` 越界回收、`MutationObserver` 动态节点卸载焦点恢复。 |
| `TOP 2 / TOP 3` | **WALKTHROUGH DONE** | 6 路由与阅读器决策闭环走查通过；非阻断体验 backlog 记入 `07_RE_REVIEW_REMEDIATION_ACCEPTANCE_REPORT.md`。 |
| `CI & Local Runtime` | **FIXED & VERIFIED** | `fc252210` + `84765be8`：`DrainingHTTPServer.server_bind` 跳过 `getfqdn` 避免启动阻塞，`macos-15` + `TZ: Asia/Shanghai` + `max-parallel: 2/3` 通过 **14 / 14** 远端 CI。 |

## 2. 交付与安全状态

- **本地预览服务**：`http://127.0.0.1:8792/` 正在运行 `84765be8`（HTTP `200`）。
- **工作区产物**：`07_RE_REVIEW_REMEDIATION_ACCEPTANCE_REPORT.md`、`RE_REVIEW_CHECKPOINT.md`、`screenshots-r2/`（7 张脱敏 PNG）仅作为纯文档/证据提交。
- **阻塞项（BLOCKED）**：无工程阻塞；**Gate R1 = HOLD（等待独立 Reviewer 第三轮复审及用户批准，严禁自行合并 `main`）**。
