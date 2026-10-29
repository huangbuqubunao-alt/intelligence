# Kimi 有界公开诊断决定

用户答复：“可以试试kimi的有没有免费方案 或者付费你也可以试试kimi”；随后确认已有开放平台API账号。该具体付费Kimi选择在原请求边界内执行：最多8次生成、单次最多预留1元、总计不超8元，质量失败停止，不自动充值或启正式日常付费；GLM5.3不调用。只发送已冻结公开YouTube样例和合成关注设定，不发送私人内容、其他QA资料或正式数据。实际Kimi调用目前0，质量未知。

官方确认认证新用户有15元代金券，但不支持K3.1Pro/K3。K2系列将于10月31日起停止向新注册用户开放，计划12月底下线，因此不作为新用户长期默认。NVIDIA原型/限期试用不冒充永久免费生产方案。来源：[账号与财务](https://platform.kimi.com/docs/guide/account-and-payments.md)、[模型列表](https://platform.kimi.com/docs/models.md)。

先测试kimi-k3.1-pro普通版，非highspeed、非旧NVIDIA K3。官方输入13元/百万token，输出68元/百万；缓存默认自动写入，5分钟写入13元/百万额外计价，保守按未缓存输入加全量5分钟写入计算，不假装只有基础输入费。来源：[当前定价](https://platform.moonshot.cn/docs/pricing/chat)、[K3.1Pro指南](https://platform.moonshot.cn/docs/guide/kimi-k3-1-pro-quickstart)。固定low思考，max_completion_tokens6144，JSON最终正文；官方固定sampling参数不显式覆盖。价格/上下文能力是官网资料，不是本项目质量通过证明。

先在文件级QA包验证质量，不写产品CP/consent、卡片或资格，不扩Schema44。独立小脚本/并发幂等/预算/泄露保护由唯一writer在readiness-kimi31-public-diagnostic实现，Root只针对固定新增改动审一次；实际发送前仍须通过这些检查。旧4.7原始失败/输出与once、旧Kimi K3 STOP和M12资格不改写或继承。

并行UI小修仅把provider级密钥设置从旧kimi-k2.6名称解耦，并补安全moonshot直达/返回/草稿清理，不改变执行型号、预算、后端凭据API或资格。新的隔离页只接com.huangbuqubunao.intelligence.qa.kimi-public-20261029/api-key，不读取原M12、正式或智谱凭据；用户本人填写，禁止聊天发送。独立83SQL/19DATA已冻结，后台worker关闭且设置服务出站拒绝。

检查实际账号余额/券适用情况前，不承诺账号可执行；需充值由用户本人操作，未用预算不自动追加调用。实际账单UNKNOWN时保留预留，不能伪造0或无声重试。完整实际结果另报。
