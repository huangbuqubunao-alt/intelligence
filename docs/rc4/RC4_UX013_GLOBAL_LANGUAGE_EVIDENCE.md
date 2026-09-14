# RC4 UX-013 Global UI Language Evidence

## Scope and authority

- Authoritative predecessor:
  `c59fad90d80bada53a872f3a490b3ac4d73235f7`.
- Round-1 MUST implementation ancestor:
  `9d0d5425e740004f4c4c056f9a55df185bf00c00`.
- Implemented scope: global product-interface language for `en` and `zh-CN`.
- Default for a missing, invalid, or unsupported preference: `en`.
- Setting location: **Settings → General → Language**.
- Language names: **English** and **简体中文**.
- Database user version: `16`; `m017` remains absent.

This amendment does not implement UX-003, UX-004, UX-005, UX-012, Deep
Analysis, TASK-016G, or V2 functionality.

## Behavior and persistence

Changing the selector updates the current React tree immediately and sets the
document language. It does not require a reload or application restart. The
presentation preference is stored locally under
`youtube-intel.ui-language.v1`, survives navigation and page reload, and is
available after a normal restart of the local application because browser-local
preferences survive that restart.

The preference is presentation state only. It is not sent to the application
API, does not mutate backend or trust state, and requires no database schema or
migration.

## Translation architecture

`frontend/src/workspace/localization.tsx` provides a small repository-native
React context, a typed static Simplified Chinese dictionary, deterministic
English fallback, interpolation, preference persistence, and `<html lang>`
updates. No localization dependency, runtime translation service, or network
lookup was added.

Components request product-owned text through the context. Existing
backend-owned readiness and Source Run projections are localized only when they
exactly match a known product-owned phrase. Unknown values and raw technical or
external detail remain verbatim; they are never guessed or rewritten.

An invalid stored locale resolves to English. A missing Chinese key also renders
its English key rather than blank text, `undefined`, a hidden action, or a page
failure.

## Canonical terminology

| English product term | Simplified Chinese UI term | Context decision |
| --- | --- | --- |
| Dashboard | 概览 | Return overview, not an engineering dashboard |
| Intelligence | 洞察 | Distilled, useful, evidence-traceable output; avoids the military sense of “情报” and the generic technology sense of “智能” |
| Topics | 主题 | Stable concept grouping |
| Sources | 来源 | Monitored YouTube sources |
| Investigations | 调研 | Reserved research workflow; still unavailable in V1 |
| Settings | 设置 | Product preferences and readiness |
| Saved | 已保存 | Saved-reference view |
| Weekly | 每周回顾 | Weekly return orientation, not a calendar label alone |
| Evidence | 证据 | Traceable support for an Intelligence claim |
| Needs Attention | 待处理 | Discoverable action-needed summary without implying universal failure |
| Resource Usage | 资源使用 | Calls, tokens, and cost truth |
| Check Now | 立即检查 | Starts one new normal Source Run; never presented as Retry |
| Analyze this Video | 分析此视频 | Relevance-only override; other guards remain |
| Initial History | 初始历史范围 | Existing recent videos considered on initial add |
| Per-run Limit | 单次运行上限 | Maximum new videos processed in one run |
| Focus | 关注重点 | User-entered relevance terms remain unchanged |
| Ignore | 忽略内容 | User-entered exclusion terms remain unchanged |
| Distillation Style | 提炼风格 | Presentation emphasis, not a model change |
| Conclusion | 结论 | Intelligence card conclusion |
| Why this matters | 为何重要 | User-value explanation |
| What is new | 新增信息 | New or changed information |
| Details | 重要细节 | Current card label |
| Fact | 事实 | Claim-kind label only; enum remains `FACT` |
| Evidence-backed statement | 有证据支持的陈述 | Visible “Supported statement”; enum remains `EVIDENCE_BACKED_STATEMENT` |
| Opinion | 归属明确的观点 | Visible “Attributed opinion”; enum remains `OPINION` |
| Prediction | 预测 | Enum remains `PREDICTION` |
| Rumor | 未确认的传闻 | Visible “Unconfirmed rumor”; enum remains `RUMOR` |
| System inference | 系统推断 | Enum remains `SYSTEM_INFERENCE` |
| Ready | 就绪 | Only for authoritative ready state |
| Blocked | 受阻 | Does not imply existing Intelligence is lost |
| Credential | 凭据 | `NVIDIA_API_KEY` remains an exact identifier and externally configured |
| Budget | 使用预算 | Independent execution gate |
| Provider | 模型服务商 | Provider identities remain exact |
| Model | 模型 | Model identities remain exact |
| Unknown cost | 成本不可用 / 成本未知 | Never “免费”, zero cost, or no charge |

## Interface language versus content language

The locale changes only product-owned controls, labels, guidance, empty states,
and known product errors. It does not translate, regenerate, or mutate:

- YouTube video titles, Source/channel names, or creator names;
- user-entered Focus, Ignore, Topic, or preference text;
- Intelligence conclusions, explanations, details, or saved content;
- Evidence excerpts, transcript text, timestamps, quotations, or URLs;
- provider/model names and literal IDs, including `NVIDIA NIM` and
  `moonshotai/kimi-k3`.

No LLM or translation API is involved. Language changes produced zero provider
calls and zero application write requests in browser acceptance.

## Trust parity

English and Simplified Chinese render the same underlying data and expose the
same legal actions. Automated coverage exercises ready, credential-missing,
budget-blocked, provider-unavailable, successful Source Run, Evidence, all six
claim kinds, and AMBIGUOUS states in Chinese. It confirms:

- AMBIGUOUS exposes details only and no Retry/Resume/Continue action;
- provider-unavailable never offers fallback;
- budget recovery never raises a limit or authorizes spending;
- credential recovery never asks for, stores, echoes, or tests a key by model
  generation;
- unknown cost remains unavailable/unknown, never zero or free;
- Deep Analysis remains unavailable and TASK-016G remains unauthorized;
- language switching does not alter Intelligence, Evidence, Source Run state,
  provider/model eligibility, or dispatch behavior.

## Automated and browser evidence

- Focused localization and UI tests: PASS.
- Full frontend tests: PASS — 40 tests.
- Frontend typecheck: PASS.
- Frontend production build: PASS.
- Real Chromium browser acceptance: PASS in `en` and `zh-CN` at 1440×900,
  1280×800, and 768×900.
- Browser console errors: `0`.
- Unexpected external frontend requests: `0`.
- Application write requests caused by language switch: `0`.
- Source configuration modal: role/name, initial focus, Tab and Shift+Tab
  containment, Escape close, and focus restoration PASS in Chinese; the
  existing English acceptance also passes.
- Horizontal overflow at all captured major surfaces and viewports: `0`.

The browser run visits Dashboard, Intelligence/Evidence, Saved, Weekly, Topics,
Sources, Add Source, Source detail, Source configuration, Source Run states,
Investigations, Settings, Resource Usage, and representative readiness states in
both languages. Screenshots were also inspected manually; product chrome wraps
without materially blocking use, while external and user-authored content stays
unchanged.

## Usability-test protocol amendment

The five-person test templates now record `TEST_LANGUAGE: en / zh-CN`. The plan
recommends, without imposing a recruitment quota, 3–4 `zh-CN` sessions and 1–2
`en` sessions. Localization-only observations must be tagged `LOCALIZATION`;
cross-language product problems remain attached to their ordinary product
category. Research questions and UX-003/004/005/012 decision rules are unchanged.

## Known bounded limitations

- RC4 supports exactly English and Simplified Chinese; it does not auto-select
  from the operating-system locale.
- No automatic translation of product content is provided or implied.
- A full Simplified Chinese user manual is not part of this amendment; final RC4
  documentation reconciliation remains after the five real sessions.
- Unknown raw external errors remain available verbatim rather than receiving an
  invented translation.
