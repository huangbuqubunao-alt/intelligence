# R13 本地拒绝响应收尾：独立审查

- Reviewer：`local_budget_evidence_audit`；日期2026-10-20；与实现者 `local_rejection_accounting` 分离。
- Base：`a989873773c0f4018cc696930789566925e88c7c`；core：`ac2ea9d4585f3215b9f2330da4062f6fed95b1f5`；完整候选：`62ed4307690cab7d2bbecca5b475695f2e922784`。
- Review WT：`/Users/developer/Documents/yia-worktrees/readiness-local-rejection-review`；branch `codex/review-readiness-local-rejection`；开工及完成检查候选 clean，源码和测试 SHA 在所有验证前后完全相同。
- **APPROVE。本任务范围未发现 P0/P1/P2。** 只接受失败收尾与诊断隔离工程；不代表模型资格、最终Goal、原失败库修复、GUI或正式采用通过。

## 依据与范围

重新读取仓库 AGENTS/协作、PROJECT_STATUS、任务卡与开工包、系统/产品持久化边界、`TASK_022C_RESOURCE_LEDGER_AMBIGUOUS_OUTCOME_AMENDMENT.md`、ADR-005及复用合同。任务/包从root只读取得；作者候选未包含后续root任务状态文档，不影响产品diff基线。按 graph-first 定位，图中无新helper，改以固定候选完整 diff/源文件核验。使用 code-review-and-quality 五轴审查。

审查完整 `base..candidate` 五文件：产品仅 `distillation.py` 与 once harness；新增一份回归文件及作者handoff/结果摘要。没有 state/Schema/profile/capacity/Backup/依赖/配置/凭据或前端变化；旧测试未删除或改写。复用 DIRECT 现stdlib HTTP/JSON、transport result、SQLite不可变usage/claim、有限AMBIGUOUS语义与独占fsync诊断，不增第三方实现或许可义务。

## 五轴结论

1. **正确性**：已知拒绝只保留响应中的真实非空model，不从选中模型补写；错实际模型仍拒绝并保留其原标识。token仅接受双侧非bool、非负、SQLite signed64内整数；缺失/单侧无效/负值/溢出整对unknown，不clamp、不补零。新profile的done/stop、6144严格上限、输入容量、公共正文/字节检查不变。legacy本地分支同样得到可靠pair保护。
2. **安全与持久化**：没有可验证身份的响应按现有 `AMBIGUOUS/1/TRANSPORT_OUTCOME_UNKNOWN` 原子落账，保留NULL身份/用量/费用；没有新成功、Evidence、资格、可取消或重发权限。原state validator及Schema有限码未放宽。独立重启/continuation、claim并发、取消拒绝、其他PENDING继续阻塞、全SQLite行和全部DATA恢复断言通过。旧R3/R4原失败库不改写。
3. **架构**：有限观测helper复用原transport result；精确拒绝原因在独占result.json的 `local_response_error` 诊断列保留，不冒充成功receipt或增加数据库authority。每次generate清空本次诊断再记录，避免前次final/completion/rawhash串案；不读取thinking。
4. **可读性/维护**：修复位于响应观察与现有错误收尾边界，helper注释明确selected不等于actual，分支有限，无无关重构。已知REJECTED_OUTPUT与未知AMBIGUOUS区分明确。历史代码/资源保持原版本，不给旧receipt重新授资格。
5. **性能/范围**：只有已有限制的响应投影与常量次数检查；不增加网络次数、模型请求、数据库表或额外读取thinking。四个Cloud transport类与旧 `LocalTextDistillationProfile` AST对base相等；七个保护文件字节相等。Cloud授权/费用与NO_NEW代表回归通过。

**未知与Backup的准确含义**：原合同允许完整、终态、账本可信的AMBIGUOUS归档，归档保存未知事实而非认定模型成功或允许重试。本审查重跑既有该正控、账本篡改负控、仍可恢复等待/PENDING阻塞及新响应的完整恢复，不把“未知”当成可安全取消的零调用等待。

## 独立实际执行

全部命令在review WT运行，使用已装共享工具路径 `V=/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin`，无安装。pytest使用 `PYTHONPATH=src:.`，额外内联探针使用 `src:.:tests`；实际导入的distillation路径已确认在review WT，非正式/作者源码。所有DB/DATA均测试临时目录。日志位于本WT ignored `.var/local-rejection-review/`。

| 命令/检查 | 本次实际结果 |
| --- | --- |
| `$V/python -m compileall -q src/youtube_intel/distillation.py scripts/qualify_local_grounding_v1.py tests/integration/test_local_rejection_accounting.py` | PASS；先于测试 |
| `$V/ruff check src tests scripts` | PASS |
| `$V/mypy --strict src/youtube_intel scripts/qualify_local_grounding_v1.py scripts/qualify_readiness_qwen35_intelligence.py` | **118 source files PASS** |
| `$V/python -m pytest -q tests/integration/test_local_rejection_accounting.py tests/unit/test_ollama_local_distillation.py tests/unit/test_distillation_dispatch.py tests/unit/test_local_grounding_profile.py tests/unit/test_local_grounding_harness.py tests/unit/test_openai_distillation_adapter.py tests/unit/test_moonshot_distillation_adapter.py` | **146 passed /40.44s**；包含全部37新增 |
| `$V/python -m pytest -q tests/unit/test_backup_restore.py tests/integration/test_task022_personalized_distillation.py tests/integration/test_task023b_distillation_reservation.py -k '<下列固定表达式>'` | **48 passed /168 deselected /27.21s**；这是明确选例，不声称完整三文件通过 |
| 内联独立legacy fake-HTTP service探针：损坏JSON、缺model、错actual、unpaired、signed64overflow；真实transport→service→state，再新repository重启continuation | **5/5 PASS**；每案只有1个fake generation POST，重启无HTTP/redispatch，无真实provider I/O |
| AST审计四Cloud类与旧Text类；七保护文件相对base逐字比较；源码/测试SHA前后比对 | 全PASS |
| 纯 `local_distillation_capabilities()` 与固定资格资源检查 | 六scope/language均NOT_QUALIFIED、records=[] |
| `git diff --check base..candidate`、完整diff、最终status | PASS；新增审查报告外无改动 |

上述 `-k` 原文：

```text
waiting_model_zero_invocation or cancel_rejects_claimed or model_wait_cancellation_requires or cancellation_does_not_change or preflight_cancel_and_dispatch or quiescence_accepts_terminal or quiescence_fails_closed_for_tampered or quiescence_keeps_resumable or completed_no_new_attention or no_new_result or ledger_sql_rejects or ambiguous_or_claimed or dispatch_claim_without or actual_model_mismatch or ambiguous_transport_outcome or cloud_dispatch_requires or openai_known_response_and_ambiguous or moonshot_known_response_and_unknown or known_cloud_http_errors or ambiguous_invocation_round_trips
```

三份最终源码/测试SHA与作者最终摘要匹配，且独立验证前后未变化：

- distillation：`daae02a09c0b17a147ad304c87c32a90068c9152f12436a92bd46c92cce3aef3`
- once harness：`9478d79f46fad8cea4065f851ba503682ef315557a966bd91830264e5dabd5b9`
- 新回归：`b389d7653fd695ed2d4342996e15ca52d27e20fee345bab9708f1a2d6d2667cb`

独立日志SHA256：focused `a72d5a7b4794ad7d2cce35d8bdf1aa31943eaea1d682e15c7a7cd5c8059f0005`；legacy-boundaries `f1416cb7debbe121b31d06ea93db8d45cf000c60ed0921eaff837953febda1c9`；independent-legacy-wire `e25d157c0a53caaa034a63f4459f7df9b38d7fc74903f1db4d75641eca917dfd`；mypy `749c760efef02805f6b5a0336f3a75504bd2c15fdd98962720faca6c94956f55`；Ruff `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`。

## 限制与交付

本次独立检查没有测试失败或中断；作者原RED/环境错误/Schema有限码失败均仍保留，不覆写。作者506PASS对应signed64增量前固定SHA，最终44PASS对应增量；本审查不混报成最终506，也未无变化再跑该全组。前端0diff，未重复前端/TS/build；最终Goal全回归与真实GUI仍待root。

本次真实网络/模型/付费Cloud/正式数据/凭据访问均0。原失败库不在本任务修写范围。模型预算仍6144、资格仍关闭；R14、新profile、完整正向样本/原资格、长内容协议、真实GUI及最终采用均是后续门禁。执行代码hash改变，不能复用旧资格receipt。

Reviewer仅新增本报告，提交后clean STOP；未修改产品/测试、未合main、未自签任务DONE。由root接受并整合后再串行推进。
