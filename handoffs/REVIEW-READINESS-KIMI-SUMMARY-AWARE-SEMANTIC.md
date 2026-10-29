# TASK-READINESS-KIMI-SUMMARY-AWARE-SEMANTIC — independent review

## Metadata and decision

- Role/session: independent Reviewer `/root/kimi_summary_semantic`.
- Base/reviewed HEAD: `e35a176212366c595ac111c37f30371c3cf1bfd5`.
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-kimi-summary-aware-semantic-review`.
- Branch: `codex/task-readiness-kimi-summary-aware-semantic-review`.
- Date: 2026-10-29.
- Verdict: **REJECT** for admission of this specific complete positive card; **one P2 finding**, no P0/P1 findings. This is not a finding that the new interview material lacks distinct value or that the model's general ability is disproved.
- Scope: exactly one bounded semantic review of the NEW actual output `public-aircAruvnKk-zh-kimi-k3.1-pro-summary-aware-1`. Only this new report is changed. No repair, retry, second review loop, model qualification, or next paid call is authorized by this report. **STOP**.

## Frozen material independently checked

`R = /Users/hua/Documents/yia-worktrees/end-to-end-user-readiness`.

| Material | SHA-256 |
|---|---|
| `R/.var/kimi-summary-aware-diagnostic/package/request.json` (actual five-message Kimi request, 21,463 bytes) | `0e464d158d2d1253c51d9c083a3e39be04cc814d8e94affcdb8d7a9a4e97f8d2` |
| Prepared identity, from `package/prepared.json` | `bf128398898afae5bcb16ac78af0c81c37edcafc874c6eee0c016026560e99aa` |
| `package/summary-raw.json` | `3130d3ca3d33f1d343edfa8ebac500bf56090b3b641a46991c453ea223408a9a` |
| `package/summary-context.json` | `dfc047f1279b04203b216e2513a2f7cccb2f47c4a46c2d4e5323b95ed0a4258f` |
| `R/.var/end-to-end-user-readiness/unseen-zh-oracle-20261029/source.json` | `5de4d66c7120c8f0944b851e7d7c63fd85ceba0b6cf35fdd4f68aae0fe428481` |
| `R/docs/validation/end-to-end-user-readiness/UNSEEN_ZH_REFERENCE_ORACLE_V1.json` | `9726b12a742accb3eb196f2995baae07c5533f70d768b47dfdac9f0193fc41f0` |
| `R/.var/end-to-end-user-readiness/kimi-public-20261029-ledger/public-aircAruvnKk-zh-kimi-k3.1-pro-summary-aware-1.public-final.txt` | `b411ec2f8bd0a1050322d728a4ae5a6793a0d08aa2dcbba1cfc2de4efa7594a3` |
| Same new-case `.result.json` | `b11c07040fbd2f72d3aeb8d001a5f61df161ab1f96773c617827f9b4844f333b` |

The prepared identity is the `prepared_sha256` field, not the file-byte hash. The actual request is `request.json`; the three-message GLM-shaped `request-body.json` is an input capture, not the final five-message Kimi wire. The final request preserves its original three messages and appends the generic comparison policy and complete current Summary representation. No previous failed output or previous semantic verdict was used to decide this review.

## Finding

### P2 — User-facing evaluation advice is classified as a source statement

Location: new `.public-final.txt:1`, `user_relevant_information[0]` together with `claim_kind`.

The card says: “理解入门示例中的 Sigmoid 不应被视为当前深度网络的默认选择；比较激活函数时，训练难易是需要单独考察的因素。” It then assigns the entire card `EVIDENCE_BACKED_STATEMENT`.

The actual added system message (message index 3) explicitly says: “Substantive own recommendations or interpretations in any returned field require SYSTEM_INFERENCE, with their basis and remaining validation stated; the single card claim_kind must not disguise them as source claims.” The original system message independently requires classifying the system's own interpretation or inference as `SYSTEM_INFERENCE`.

E07 reports the interview exchange: the host contrasts then-current usage with the tutorial's Sigmoid; Lisha answers that ReLU is easier to train, defines `max(0,x)`, and describes its good performance. It does not give the product user an activation-function evaluation rule. The quoted field turns that report into advice about what the user should treat as a current default and what the user needs to assess separately. That is a substantive recommendation derived by the system, even though the underlying motivation is supported. It therefore changes the epistemic role of part of the card; it is not merely a label saying why this source concerns the user's focus. Its unconditional “当前” also sits outside the core sentence's explicit attribution to the interview.

This finding is based on the guidance conveyed, not on the mere presence of “不应” or “需要”. The core interview paraphrase itself can properly be an `EVIDENCE_BACKED_STATEMENT`. The caveats that the video lacks benchmarks and that a biological analogy is not proof are reasonable descriptions of evidentiary limits; they are not independently counted as misclassified substantive inventions. The output already supplies a basis and acknowledges missing validation, which limits severity. Nevertheless the single card classification does not satisfy the sent rule for the complete returned card. No output text or classification was repaired during review.

## Acceptance results and counterevidence

| Dimension | Result and concrete basis |
|---|---|
| Real Summary comparison | PASS. Independently restored all ten Summary fields using the final request's Unicode substring rule. They equal the captured actual raw fields exactly, and the captured raw equals `source.summary_json`. The six extractive core points cover E01–E06; neither ReLU nor Lisha is present. This is no longer a missing-baseline assessment. |
| Distinct positive retention value | PASS for the selected material. The E07 interview adds the ReLU/Sigmoid training comparison absent from the full real Summary. The card preserves the distinction between reported training advantage and independent measurement. This is useful bounded context for the supplied reliability/verification focus, rather than sponsorship, 784/16/13,000 repetition, or a forced business opportunity. The REJECT does not negate this positive evidence. |
| Core factual accuracy and attribution | PASS within the supplied caption authority. The core names Lisha and attributes the comparison to her; the definition and qualitative training advantage are supported by E07. It invents no numerical gain, convergence guarantee, test-time result, or measured reliability. “现代” in the attributed core is read as the interview's reported claim, not as independently verified 2026 prevalence. No absent publication date or external current-practice knowledge is required. |
| Modality and source limitations | PASS for the attributed interview content. “视频未给出训练基准或独立验证” and “未提供量化证据” preserve limitations. The biological passage remains an analogy. The caption's misleading “权重介于0到1” is not amplified into a claim that all weights are bounded; the output's neuron-output wording is consistent with the supplied earlier explanation. No separate factual finding is raised for this. |
| Whole-card claim classification | FAIL: the P2 finding above. The direct source report and the system's own evaluation guidance must not be conflated under one source-statement classification. |
| Reference, stance, and positions | PASS. Sole citation `E07/supporting` resolves to exact canonical Evidence `129af1f23ea80e65d50fc96fc7f1a104cc6e6602443515006a5bc5cd7aca4888`, 1,013,589–1,106,060 ms, cues 209–230. Its excerpt is exact and its stance supports the interview report. No relevant contrary measured result is supplied or hidden. No foreign reference, timing field, or model-produced Evidence ID appears. |
| Structure and language | PASS in the bounded offline inspection: one strict JSON object, exact eight positive-result keys, correct string/list types and enum, required protocol, Chinese generated text, no fence or extra text. This is independent structural inspection, not a claim that the entire production validator or product path was rerun. |
| NO_NEW behavior | Not exercised: this actual output is positive. NO_NEW would be permitted if nothing qualified, but would not prove positive coverage. No specific positive conclusion was demanded. |

## Checks, scope, reuse, and limits

- Read the repository guidance, collaboration/specification/status/reuse documents, assigned task and reviewer prompt; used the unchanged exact request, source, Summary, and oracle as authority. Reuse decision: **DIRECT** existing frozen data and documented Summary substring semantics; Python standard-library `json`/`hashlib`/`pathlib` for bounded read-only inspection. No third-party code copied, dependency installed, or license obligation introduced.
- Executed a bounded `python3` inline read-only check: strict JSON with duplicate-key rejection; hashes; exact eight-key output shape/types/enums/protocol; Summary ten-field restoration; source/oracle snapshot equality; all 231 cues/seven Evidence; all seven sent excerpts reconstructed exactly from their canonical cue ranges; E07 canonical identity, position and excerpt hash. **PASS**, process exit 0. The preceding independent hash inspection also matched all task-pinned file hashes.
- Executed `git diff --check` and reviewed the report-only diff before commit; no product or evidence file changes. No whole test-suite rerun, full code review, production-validator rerun, Native action, API/model call, credential read, network access, or ledger sidecar write was performed. These are outside this assigned bounded review.
- The new result file reports HTTP 200, `kimi-k3.1-pro`, `stop`, 6,583 prompt tokens and 566 completion tokens including 287 reasoning tokens. It retains actual bill `UNKNOWN` and semantic `NOT_REVIEWED`; this report does not mutate either. Accounting, SQL/DATA invariance and backup-readiness proof remain Root's independent scope, not evidence re-proven here.
- No unresolved P0/P1 findings; one unresolved P2 prevents approval of this exact whole card. The new raw output, result, frozen oracle and old failure remain unchanged. This is one case, not model/product qualification, a Save/Topic acceptance, or proof that normal execution is usable.
- Reviewer conclusion: **REJECT / clean STOP**. Root decides the next action; no additional generation, review loop, payment, integration into `main`, or task-status change is performed by this reviewer.
