# 通用grounding v2候选整合核对

作者86ea+兼容修复f878，经独立c86b6104累计APPROVE；原15f72e6 REJECT保留。Root整合cea14bd/3081e27/4c01997后src/tests/frontend逐字等f878。仅通用prompt wrapper/独立资格profile和v2专用输入子类，无Schema、依赖、正式配置或正常资格变化；旧base19字段/projection/提示词保持原样，不放宽旧consumer。原字段泄漏导致的历史export/long hash问题已补因果回归，未靠跳过断言解决。

Root内存编译123、strict mypy122、Ruff通过；6个完整相关文件329PASS87.20s，包含原失败harness/long projection/profile、新v2、实际service及BackupRestore。唯一warning来自原有故意重复ZIP路径拒绝测试，没有抑制。作者16文件704PASS221.15s和独审12文件483PASS104.37s为分别独立证据，不相加，也不冒充全后端最终回归。

Root另用**真实v1请求后的隔离数据库**只读复制到新QA目录，用当前已审v2代码重建旧prospective输入：实际semantic hash仍4d4b307…150e、execution ID不变、原4132B wire逐字相等、旧调用数仍1。随后用当前代码实际Backup→stage→confirm→recover；全部81表每行/Schema和19DATA相同、readytrue，原case和已耗标记未改。新ZIP SHA `0745c249655c6d0dfd93ce950ce331baa2da6bbaeeaad039ef63e83ec6a7a4b9`。核对记录位于隔离QA的`root-v2-real-v1-history-20261028/root-proof.json`，没有key、预算或网络访问，没有重新调用模型。保留旧结果的语义REJECT，不把工程历史可读当模型质量通过。

正常模型资格/预算仍关闭；独立oracle6760fd0…f9cc2已冻结且未用于修改prompt。Root接受本片段仅意味着可准备下一份严格绑定的公开诊断包；新具体源/profile/请求/代码/价格/once包独立审查前不能执行。单例真实通过也不等于完整资格、普通用户全链路或main采用。正式main和owner数据不变。
