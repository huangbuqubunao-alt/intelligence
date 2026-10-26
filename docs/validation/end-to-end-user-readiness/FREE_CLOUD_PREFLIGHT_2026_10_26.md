# 免费云候选：事实与验收边界（2026-10-26）

选择智谱标准 API `glm-4.7-flash` 为首个免费云候选，**尚无账号完成、真实生成或质量资格**。用户表示会自行注册后通知；不代表已经注册或授权充值。继续工程，不等待账号，不再下载本地模型。

| 项目 | 官方事实和当前证据 | 边界 |
|---|---|---|
| 价格 | [定价](https://www.bigmodel.cn/pricing) 明确此模型当前输入、输出、缓存免费 | 精确型号，不能把所有 Flash 视为免费，不承诺永久，不自动转付费 |
| 模态 | [模型指南](https://docs.bigmodel.cn/cn/guide/models/free/glm-4.7-flash)：文字输入输出、200K context、128K 最大输出、JSON/思考模式 | 规格不是质量证明，不能继承为转写或摘要资格 |
| 接口 | [API 文档](https://docs.bigmodel.cn/api-reference/模型-api/对话补全)：HTTPS POST `https://open.bigmodel.cn/api/paas/v4/chat/completions`、Bearer、非流式/max_tokens/JSON object | 标准库固定端点，无新增SDK；只接纳公开 final，不把 reasoning_content 当 Evidence |
| 注册 | [FAQ](https://docs.bigmodel.cn/cn/faq/authentication-issues)：当前 API 不强制实名 | 用户自行注册，不代办实名/接受条款；零余额可用仍待本人账号实测 |
| 限流 | [速率文档](https://docs.bigmodel.cn/cn/api/rate-limit)：账户权益及模型并发限制、峰值动态保护 | 实际额度查本人控制台，不能承诺无限；429 不自动重放 |
| 隐私 | [政策](https://docs.bigmodel.cn/cn/terms/privacy-policy)：境内存储、必要保留期限、匿名数据可用于服务及模型改进 | API 专属零留存/训练豁免未核实，首轮只用公开/合成样例，不发私人文件/兴趣 |
| 网络 | 07:45:51 UTC 精确接口无密钥、无正文 HEAD：HTTP401、TLS校验0、1.320409秒 | 仅当前代理链连通和正常鉴权拒绝；remote_ip=127.0.0.1 是本地代理，不证明直连或账号/模型可用 |
| 实际使用 | 无认证生成、usage、账单或语义验收 | 全部未验证，不授资格，不套旧 Kimi 或本地资格 |

十份公开原始快照和 SHA 清单在 `.var/end-to-end-user-readiness/free-cloud-preflight-20261026/sources.json`，通过 agent-reach 网页路由获取，无密钥或私人数据。HEAD 没有执行生成。未购买搜索配额或升级工具。

## 最小后续范围

先完成唯一 cloud-readonly-preview 提交、独立审查，再从已接受基线串行适配，不并行改共享状态/授权。`REFERENCE` 官方协议、`DIRECT` 已批准标准库HTTPS/JSON/SQLite、`ADAPT` 现有有限云 transport 与 sealed-input/claim/receipt；无新依赖或锁文件，不重新开发框架。

1. 明确唯一 provider/model、固定 endpoint/request profile、有限输出和等待、零自动重试。不得冒充 Moonshot/OpenAI，不允许 FlashX/GLM5.x 付费回退。
2. 先离线验证 canonical Evidence、精确数据披露、provider-specific 凭据、响应/429/未知执行和零费用策略。密钥只在隔离设置页输入，不进聊天/日志/命令行/Git；配置成功不等于质量合格。
3. 现有 consent/unknown/response-failure SQL 约束仅列原 provider。新 tuple 不可仅扩 Python 白名单绕过数据库保护。先写精确迁移、旧34–41/新版本恢复、历史保留和失败回滚方案；本文件未实施或假定具体新 Schema。
4. 冻结公开样例、原语义/Evidence标准、profile、最大调用数及停止规则。真实调用前核实本人账号该精确免费 entitlement，无充值/套餐；要求付款即停止。保留逐次同意/一次派发/未知 fail-closed，失败不修补输出制造成功。
5. 真实验收必须走 Content→字幕/摘要/Evidence→明确云同意→洞察→保存/主题/引用回跳→重启→全 SQL 行与物理 DATA 的 Backup/Restore，一并完成整体验证。公开视频资格不能自动扩 LOCAL/BILIBILI 私有上传、转写或摘要能力。

收费路径无真实预算策略即拒绝调用。Gemma 拒绝/once/全部失败保留，正式 main/配置/数据不动。没有账号时继续工程、离线验收及审查；不伪报云端真实可用。
