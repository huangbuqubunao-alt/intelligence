# TASK-READINESS-TRACKED-CONTENT-RETRY — 独立基础检查点评审

2026-10-18；Reviewer `tracked_foundation_review_oct18`。**阶段结论：REJECT**。

审查对象：`c312ee4a544556616c9b102d57ec44cf56a21b90..43e0c751291b0b42423fb7c3c2f3bf238ba1f4de`。独立快照 WT `/Users/hua/Documents/yia-worktrees/readiness-tracked-foundation-review`，branch `codex/review-readiness-tracked-foundation`；初始 HEAD 精确为作者检查点且 clean。未在作者 WT 执行或写入、未读取其后续产品改动；只查看过其 `.venv` 链接元信息以定位现有共享解释器。未访问正式数据库、owner/Vault/config/credentials、模型 holdout 或私人语义控制集。

本次只评审040三表、冻结 admission/基础 reader、稳定锁、generic 隔离。worker/HTTP/child/file writer/Backup/API/UI 尚未完成是已声明的后续范围，**不以这些尚未完成本身作为本次拒绝理由**。以下三项发生在已经提交的基础合同中。此结论不授 main 采用，不代表完整任务验收或完成。

## 必须返修的发现

### F1 — P1：generic ambiguous 写入口绕过本协议 provider authority

位置：`src/youtube_intel/state.py:4149`，尤其同事务 `:4157`；对照新增加的其他 provider guards。

`mark_provider_dispatch_ambiguous()` 没有调用 `require_provider()`。只要提供现有 logical owner 和未过期 lease，就会调用 `_mark_dispatch_ambiguous_in_transaction()`，把本协议 provider call 改为 `FAILED_FINAL`、dispatch 改为 `AMBIGUOUS`；不需要 request 锁、execution epoch 或专属 authority check。该入口因此可以在执行者仍持锁时独立改写其 provider 历史，破坏新协议对 generic 路径的隔离。

独立反证 `test_generic_ambiguous_mutator_must_reject_owned_hash`：通过普通 Following/runtime 离线 fixture 建立 tracked admission，仅在 fixture setup 的显式 authority 中建立 owned reservation 和 durable intent；退出 authority，再调用上述 public repository 方法。预期 `RetryConflict`；实际调用成功，pytest 报 **`DID NOT RAISE RetryConflict`**。没有真实 HTTP 或模型调用。提案§4要求“generic provider reserve/recovery也不得接管本协议provider hash”“只有专用上下文、锁、epoch与完整request验证同时通过”。请在该入口/共享底层增加一致 guard，并补无 authority/错误 epoch/仍持锁的回归，不只补 reserve 测试。

### F2 — P2：基础 reader 接受损坏历史和矛盾投影

位置：`src/youtube_intel/tracked_retry_store.py:93`、`:110–121`。

当前 `read()` 只检查 event 外层键、prior state 链和 revision 单调；没有验证 event enum、action 的固定 typed 合同/hash/输入/receipt、event epoch 与投影关系，也没有核对当前 target 状态与 execution 状态，或重验 admission 所依赖的最后旧 attempt 同码终态证据。`TrackedContentRetryService.request()` 的历史重放直接依赖该 reader 并返回 public 状态。

五个独立持久损坏负控全部 **`DID NOT RAISE RetryIntegrity`**，均未移除或关闭 schema trigger：

- 在允许的 `QUEUED→FAILED` SQL transition 中追加 `FUTURE_UNKNOWN_EVENT`；
- 同一 transition 中 action 改为 `{"arbitrary":"not a receipt"}`；
- event `fencing_epoch=999`，execution epoch 仍0；
- execution 仍 `QUEUED`，target 已直接变为 `FAILED_FINAL`；
- 原 consumed job 行仍完整不变，仅最后 attempt 的 error 改成 `UNKNOWN_PROVIDER_STATE`。

上述请求均仍能历史重放。前三项还会返回伪 `FAILED` projection，而 target 实际仍 `PENDING`。这不是要求在本检查点提前实现文件/Summary 成功证明；要求基础 reader 对它已经读取并宣称可信的事件、终态证据和 job/execution 一致性失败关闭。提案§3.2明确要求 typed verifier 进行 event/receipt 转换重放，未知/伪造/丢失事件拒绝；§4 admission 要求最后 attempt 的同码明确终态。

### F3 — P2：040 VERIFIED 文件组合约束可被 NULL 穿透

位置：`src/youtube_intel/migrations/040_add_tracked_content_retry.sql:109–112`。

`VERIFIED` 分支仅使用 `observed_sha256=expected_sha256 AND observed_size_bytes=expected_size_bytes`，没有要求两个 observed 列 `IS NOT NULL`。SQLite `CHECK(NULL)` 通过，因此状态 `VERIFIED`、settled_at 非空而 observed hash/size 均空的行可以持久化。独立 probe 对合法 request 插入该组合，预期 `sqlite3.IntegrityError`；实际 **`DID NOT RAISE IntegrityError`**。提案§3.3要求 VERIFIED 的实际 observed hash/size 精确等于 expected，不能在 schema 层留下“已验证但无观测证明”的合法行。请补非空条件及 INSERT/PLANNED→VERIFIED 的组合负控；后续文件 reader仍须独立验证真实字节。

## 独立运行的检查

解释器复用已存在的 `/Users/hua/Documents/yia-worktrees/v1x-local-main/.venv/bin/python`，没有安装/更新依赖或写入该环境。以下产品测试均在本 snapshot 的源码和独立 pytest 临时 SQLite/DATA 上运行；CredentialStore autouse 隔离保持。

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. <python> -m pytest -q \
 tests/integration/test_tracked_content_retry.py tests/unit/test_state_transitions.py \
 tests/integration/test_state_store.py tests/integration/test_provider_dispatch_crash_recovery.py
78 passed in 22.98s

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. <python> -m mypy src
Success: no issues found in 108 source files

<venv>/bin/ruff check <本diff七个Python文件>
All checks passed!

git diff --check c312ee4...43e0c75
PASS
```

补充私有 probes 位于本 WT 已忽略的 `.var/foundation-review/test_private_probes.py`，没有修改产品或正式 tests：

- 同 command 改 expected job、历史 paused/adapter 不可构造仍重放、两个 command 并发仅一次消费、active SourceRun/check/unknown/paused/trust 拒绝，在上述78项中独立复验通过。
- `-k 'other_generic or orphan_future'`：**9 PASS / 7 deselected，5.18s**。owned hash 的 reserve/recover/intent/known-failure/fail 均拒绝；无关联未来 `v99` job 在 PENDING/RUNNING/RETRY_PENDING/FAILED_FINAL 下拒绝 generic create/claim/reclaim/activate/renew/rerun/failed-list，dump 无变化。
- `-k 'cross_process_same_inode or populated39'`：**2 PASS / 16 deselected，0.97s**。实际子进程持 store SH/request EX；父进程核对两锁 device+inode，替换隔离 DB payload 后仍同 inode、request/Backup EX均 BUSY；子进程退出后可取得同一 inode。另在非空39 tracked fixture（真实 jobs/provider/tracking/artifact 行）注入040失败，完整 SQL dump/user_version保持39，正常升级40后旧领域表每行和全部隔离 DATA bytes保持，FK检查空。
- 原测试差异已人工复核：039 SQL未改；原 `history_after[37] == (39,...)` 断言保留，追加040断言；最新版本/table/index/checksum计数更新属于新增040的预期，没有删测试/减断言或改脚本隐藏失败。

## 失败证据及审查边界

私有首轮 `.var/foundation-review/private-probes.log` 为 **12 FAIL / 4 PASS，8.97s**：其中以上 F1/F2/F3 对应7个真实负控失败；另5个为 reviewer harness 的参数/异常类型写错（fail_provider_call 的 retry_at 签名、create_job 应期待 IntegrityConflict），不能算产品缺陷。原日志保留；仅修 harness 后重跑原应绿9项并通过；七个真实负控未循环重试、未改产品使其变绿。

可复验当前 probe 的七个已确认失败：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:. <python> -m pytest -q .var/foundation-review/test_private_probes.py -k 'generic_ambiguous or reader_must or verified_file'`。审查期间未再次运行此失败集合。

保留文件 SHA-256：

```text
private-probes.log       9b8bb362f2dd8fbf0bd45e43ddaee95065c55268d90e04a1a084492e020178b8
private-green-probes.log 4d2a3fb316cc82756183393808d6976dec40fad76c850237faf3dc9dec005cf4
lock-migration-probes.log bb60e92e9946e56f432eb090df78b45ff5afdced6453d47c7210bd4d1718c48d
test_private_probes.py   1df82ec3274fc218cb75cd1d1da4a98f7d95fc990ffda9e14b10dd4a5b328497
```

Codebase graph优先查询已执行，已索引项目无新 tracked retry 符号，因此以精确43e0c75源码 fallback；没有重新索引。Jev advisory仅一次请求，HTTP451不可用，继续原严格review，未降级或重试。复用评审采用 `code-review-and-quality`；DIRECT标准库 SQLite/fcntl 和现有 managed_directory/provider hash/tracking边界，无新依赖、第三方移植或许可证变化。

没有运行完整 backend、frontend/build、34–40真实 BackupRestore矩阵、worker/child/HTTP窗口或GUI；它们属于完整任务后半，仍须作者完成后独立审查及 root 真实旧 tracked 副本验收。0真实模型/付费/业务外部网络IO，0正式数据写入；reviewer只提交本新 handoff。**返修后再审；本阶段不 ACCEPT，不合并、不发布，clean STOP。**
