# 固定证据引用协议：最小隔离适配

目的：让不同模型选择明确的证据引用，避免让生成器复写可信记录中的时间或字符位置。保持产品框架、原事实质量和Evidence标准；这是新的预先定义协议，绝不接受或修补旧v1/v2已经返回的错误时间。当前失败、原请求、旧profile、oracle、账本及once全部保留。

范围：增加一个小型、纯的请求内引用codec与一个明确版本的BigModel qualification-only v3 profile，复用已审v2事实/归因/推断要求、同一固定GLM型号/端点/参数/限额/零重试。按完整可信输入建立稳定唯一短引用（如E01），模型只输出引用与现有stance，其它文本/claim_kind/字段保持原文。后端只查该次完整、已校验且hash绑定的Evidence映射，取真实ID和原位置，交给原authority validator；不能接受模型时间、任意ID、未知alias、跨input映射、遗漏必要NO_NEW全引用或额外字段。v3原始公开输出与规范化结果可在隔离回执中区分，不能称为旧协议原输出已通过。语义/事实正确性仍须独立验收。

实现上优先小型新module+新adapter/profile，按需仅改distillation.py的有限profile/精确类型/输入投影选择与cloud_wait_cancellation.py有限版本匹配；新测试及handoff。没有Schema/依赖/配置/UI/credentials/正常生产资格变更。旧base dataclass/asdict/projection、v1/v2请求和parser、001–043、成功usage/预算/授权/dispatch/保存/读取/Backup规则均保护。新profile必须进入现有request-profile→semantic hash→reservation→不可变consent的完整绑定；新WAIT0仍安全可取消，不能重现备份永久阻塞。不能为了加profile放宽旧类型、许可或验证。

模型返回的正文、归因、数字、推断类别、stance不允许自动修正、补写或升级；只解析新协议已声明的引用表示，可靠原位置来自真实Evidence。未知/重复/非法/外来/篡改引用 failclosed；文件/hash/来源不合法仍拒绝。新协议输出若携带旧式timestamp/id或不符合精确schema，拒绝而非忽略或“修复”。NO_NEW原安全规则保持。

测试先离线：合成输入引用roundtrip/位置不丢失/字符Unicode/多Evidence完整无截断、输入变化hash和cross-input拒绝、非法字段与重复/foreign引用拒绝、实际strings/claim_kind/stance不变、NO_NEW完整与不完整、旧v1/v2完全不变、已执行/unknown仍failclosed、新v3缺key/knownTLS0取消/重启/备份兼容。复用标准库和现有校验器，不新造持久化/恢复框架。

一份固定候选的针对性代码检查即可；不重审已接受的整个历史、不重复全套629或6000。任何真正的安全问题修后仅验证对应增量。接线且审查通过前零模型/Native/Keychain/network。后续真实验收另由Root冻结未见公开样例与原标准oracle，先最多一例、任何失败即停；旧失败不能算作独立新通过。此提案不授权真实调用，不放行生产或改main。

风险：把表示适配误做语义修补、映射未绑定input、alias漏项或错误地授予旧profile许可。以精确版本/完整输入hash/严格codec/旧byte保护/旧失败不回写约束。若最小接线需要大规模重构或新持久化则停止扩张并报告替代最小方案。
