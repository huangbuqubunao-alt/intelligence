# TASK-ANTIGRAVITY-QA-LAUNCH-ISOLATION 交接

- Role: Implementer `/root/qa_launch_isolation`
- Date: 2026-11-04
- Base: `f0e330129ad9243423a0c03feb598992e94517b1`
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-qa-launch-isolation`
- Branch: `codex/readiness-qa-launch-isolation`
- Status: IN_REVIEW; Root reviews this delta once. No merge or deployment.

## 修改与复用

DIRECT 复用本仓库 Native Keychain API、正常 runtime/loopback API/worker 生命周期、已批准的 Python 标准库。ADAPT 原 serve-api 的关闭/恢复重启规则；未新增依赖或借用其他项目代码，仓库原有许可证边界不变。

新脚本 `scripts/validation/serve_user_readiness_candidate.py` 固定使用本工作树 `.var/user-readiness-candidate`。拒绝外部根目录、符号链接、硬链接数据库、非 loopback host 参数和非法端口；在初始化 SQLite/凭据之前校验。独立 DATA/logs/templates/vault 目录仅在持锁后创建。单 owner 锁覆盖整个恢复重启周期；每次重建之前重新校验路径。数据、vault 和数据库不接受用户配置路径。

Moonshot QA 固定 Native service 为 `com.huangbuqubunao.intelligence.qa.kimi-public-20261029` / `api-key`，BigModel 复用已有 `MacOSBigModelQACredentialStore`，不允许 HTTP 选择 namespace。ModelSettingsService 增加 trusted-only 环境回退限制，默认 True 保留既有产品行为；QA 关闭回退，钥匙串缺失或故障均不能退回环境密钥。显式注入的 store 通过 None 判断，不会因其假值退回正式 store。

runtime 增加 trusted-only `allow_cloud_execution`，默认 True 保持原产品默认。QA launcher 传 False，并在内存配置固定 `cloud.enabled=False` 和 local-only，避免其他云摘要/分析 Provider；不加载正式或候选配置文件，而复用仓库的无密钥 example 后绑定自有路径。API 新增同义的只读 runtime 限制，review 给出 `CLOUD_EXECUTION_DISABLED`，confirm 409 拒绝；transport 自身 cloud_enabled=False，绕过 UI/API 直接服务确认也拒绝。历史 K2.6 QUALIFIED 事实保留，费用限制只关闭当前 runtime 的执行/production_eligible，不授予新模型资格。Root 明确同意此最小 `local_api.py` 扩展。

## 实际验收

| 检查 | 结果 |
|---|---|
| 新回归文件 + 既有 model settings/local API/runtime composition 完整文件 | **90 PASS，58.17秒** |
| strict mypy `src` + 新 launcher | **130 source files PASS** |
| Ruff 三个修改源文件、新脚本、新测试 | **PASS** |
| compileall 修改源文件、新脚本、新测试 | **PASS** |
| diff 检查 | 见提交前检查，所有新增文件也纳入暂存检查 |

测试使用真实隔离 SQLite 与真实 service/API，只有外部存储/Provider 边界为 fake/spies。两种 QA Native service/account 经过原生方法的框架 spy 检查，测试不加载真实 Security framework。环境毒化、空存储/故障、保存后删除、刷新服务均不会使用环境凭据。直接 API 确认和直接 service 确认被拒绝，整个数据库 dump 不变、wire spy 0 次；metadata 明确历史资格不变且 execution disabled。

真实本机 loopback 测试使用 FakeStore 和临时端口，正常 application/handler/worker 实际启动，GET settings 200 且环境密钥不出现，随后正常关闭；没有外部网络或模型请求。恢复重启使用生命周期 fake，仅声称持锁、stop/start、signal handler 恢复验证，不声称再次做过真实有数据 Backup/Restore。真实凭据服务本任务从未启动。

组合测试工具完成记录：`.var/qa-launch-isolation/combined-check-result.json`。无真实密钥、无付费调用、无正式数据/配置、Schema、依赖或其他 Agent 文件变更。

## 失败与修正

- 首次测试未带 PYTHONPATH，collection 找不到 package，补上正确命令后得到预期 3 个 RED：新限制参数不存在。实现后全部通过。
- Native spy 最初从另一个测试模块在 autouse 后导入原 get，实际捕获了隔离替身，4 次调用断言少一次。改为本测试模块 collection 时保留原方法；断言仍保持 4 次，未削弱覆盖。
- 真实 loopback 初次启动发现 DATA/vault 尚未创建（FileNotFoundError），诊断后在验证/持锁范围内建立固定目录。之后 HTTP 探针请求了不存在的 GET credential 路径（404），按既有真实 API 改用 GET settings；最终 200。

## 运行说明与限制

供 Root 审查后使用的入口：

```sh
PYTHONPATH=src /Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python scripts/validation/serve_user_readiness_candidate.py --port 6378
```

从本候选 checkout 运行，固定新隔离数据目录，不复用此前不安全命令。此命令会读取专用 QA Keychain，因此本实现任务没有执行它；测试全部使用 fake stores。保持原 Antigravity 工作树及其文档原样，Root 可在最终统一候选中更新启动说明。

这只是 QA 启动安全修复，不代表完整用户链、GUI、模型质量或正式发布验收。模型接线、现有 Schema44 授权完整性修复和最终完整回归仍由 Root 管理。普通源码当前仍以历史 K2.6 执行通道为主；新 K3.1 资格依旧关闭。未执行完整后端或前端（无前端变更），未读取真实 QA/正式密钥。

## Reviewer / 主控

待 Root 固定 SHA 审查；未自设 ACCEPTED/DONE，未 cherry-pick、merge main、push 或启动服务。
