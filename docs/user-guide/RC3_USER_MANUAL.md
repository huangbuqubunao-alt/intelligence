# YouTube Intelligence Agent v0.1.0-rc.3 User Manual

This is the user-facing manual for the private v0.1.0-rc.3 product at commit `9422c08761eb5cb996758edee26d698dadfd901a`. It describes current V1 behavior only.

For a shorter first-use path, begin with the [Quick Start Guide](RC3_QUICK_START_GUIDE.md).

## 1. Product Overview

### What problem it solves

Following useful YouTube channels can create more video than a person has time to watch. YouTube Intelligence Agent monitors the Sources you choose and turns relevant video information into concise Intelligence that can be traced back to the original video.

The intended result is not a processed-video log. It is an answer to:

- What matters now?
- What changed?
- Why should I care?
- What kind of claim is this?
- Where did it come from?

### What it does

In rc.3, the product can:

- store YouTube Sources and monitor them on a manual, daily, or weekly schedule;
- consider a bounded amount of initial history and new videos per check;
- use Focus and Ignore terms for relevance selection;
- turn relevant videos into evidence-linked Intelligence;
- distinguish claim kinds and New/Updated/unavailable lifecycle states;
- connect Intelligence to Source, video, timestamp, and transcript excerpt;
- organize information through Topics, Saved, and Weekly;
- show Needs Attention and Resource Usage without inventing missing values;
- use NVIDIA NIM with `moonshotai/kimi-k3` for qualified V1 Video Distillation when all runtime, credential, budget, source, and trust gates allow it.

### What it does not do

The product does not:

- replace the original video as the source of truth;
- guarantee that every statement in a video is true;
- make Deep Analysis or Investigations available in rc.3;
- silently switch provider or model;
- automatically retry an external result that could not be confirmed;
- treat unknown cost as zero;
- let Analyze this Video bypass safety, trust, budget, model, or provider rules;
- provide a browser field for an API key;
- package a complete one-command ordinary-user production UI launcher in this tag.

Information may be compressed, but its source must remain reachable.

## 2. Core Concepts

### Source

A Source is a YouTube channel or supported individual video you add to the product. A channel Source can be monitored for new videos. Disabling monitoring affects future checks only and does not delete existing Intelligence.

### Video

A Video is an item discovered under a Source. It may be relevant, skipped by relevance rules, waiting for processing, completed, or blocked. A Video is evidence input; it is not automatically an Intelligence item.

### Intelligence

Intelligence is a concise, trusted product output about something useful learned from a video. A card contains a conclusion, relevance, new information, important detail, claim kind, lifecycle state, and Evidence.

### Evidence

Evidence is the trace from an Intelligence claim back to the original material: Source, video, timestamp, and transcript excerpt. Technical provenance is optional diagnostic information about the stored evidence identity.

Evidence shows what the source said. It does not create independent proof that the source is correct.

### Topic

A Topic is intended to be an understanding that changes over time, not just a folder. It can show a current state, supporting or unavailable contributions, a timeline, disagreement, uncertainty about source independence, and related Topics. rc.3 Topic views are basic and may not yet explain every change in depth.

### Weekly

Weekly is a historical view of what the product considered important during a week. It can state that no important change occurred and can show when a later trusted revision corrected a historical item. Historical output is not silently rewritten.

### Saved

Saved is your personal reference list for Intelligence you want to revisit. Saving does not turn content into a permanent stale copy. If the current trusted item becomes unavailable, the saved reference remains but its old detail is not shown as current truth.

### Needs Attention

Needs Attention means the product cannot safely proceed without a prerequisite, a clear decision, or operator review. Existing Sources and Intelligence remain unchanged unless the message explicitly says otherwise.

## 3. Starting the Product

### If someone else installed it

Open the local URL supplied by the installer/operator, normally a `127.0.0.1` address. Confirm that the header identifies YouTube Intelligence Agent and the navigation includes Dashboard, Intelligence, Topics, Sources, Investigations, and Settings.

### Repository-supported loopback workflow

The current local API is started from the repository root after the package, local configuration, and state database have been prepared:

```sh
youtube-intel serve-api --database /absolute/path/to/state.sqlite3 --port 8765
```

Start the frontend in a second terminal:

```sh
YIA_API_BASE=http://127.0.0.1:8765 npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173/`.

The API and UI bind to the local computer. The standard `serve-api` composition does **not** include the normal-production Source executor in rc.3; Check Now therefore fails closed in that composition. A normal-production Source Run has been confirmed for the authorized provider path, but its composition is not packaged as a general end-user launcher in this tag.

### Installation and configuration check

The installed command `youtube-intel doctor` performs a read-only check of local configuration and prerequisites. It does not create or repair the state database and does not call the cloud provider. Installer-level configuration uses local `config/settings.yaml` and `config/channels.yaml` files created from the repository examples; never commit local copies containing private paths or settings.

### Credential setup

The product UI has no credential entry field. The validated NVIDIA credential name is `NVIDIA_API_KEY`, supplied indirectly to the production process. Do not print it, add it to tracked configuration, paste it into the browser, or include it in screenshots.

Settings shows credential/model readiness only as safe status. It never reveals the value.

## 4. Dashboard

Dashboard is the main return point.

### What matters now

This section shows prioritized current Intelligence. Each card should be read as a finding, not as a video recommendation.

Read the Conclusion first, then Why this matters and What is new. Use Important details for qualifications. Claim type tells you the nature of the statement; New or Updated tells you its lifecycle, not its truth level.

### Topic changes

Topic changes points to an evolving subject that has changed or needs re-evaluation. Open Topics for the current understanding and timeline.

### This week

This week is a compact entry to Weekly. Use it to catch up after several days, not to audit every processed video.

### Needs Attention

Needs Attention identifies work that could not safely proceed. In rc.3 this area may appear below long Intelligence cards, so check it whenever a run appears stuck or nothing new arrives.

### Empty Dashboard

If there is no important Intelligence yet, add a Source. An empty Dashboard can also be a valid result when no video produced a meaningful change.

## 5. Sources

Sources control what the product monitors and how it selects work.

### Add Source

1. Open **Sources**.
2. Select **Add Source**.
3. Enter a supported YouTube channel URL, handle URL, or individual video URL.
4. Choose a processing level.
5. Choose monitoring, relevance, style, and schedule settings.
6. Select **Add Source**.

If the URL is rejected, use a complete YouTube URL such as a channel handle or watch URL. rc.3 may show a generic validation message rather than identifying the field.

### Processing level

- **Discover new videos only:** keep track of discovered video items without asking the product to turn them into Intelligence.
- **Turn relevant videos into Intelligence:** use the configured relevance and trusted processing path to create Intelligence when allowed.

### Enable / Disable

**Monitor this Source** controls future checks. Turning it off does not delete existing Intelligence, Saved references, Topics, or history.

### Initial History

Initial History is the number of recent videos considered when the Source is first added.

Example: Initial History 5 means the product considers up to five recent existing videos for the first bounded selection. It does not mean the entire channel is imported.

Choose a small number first. A larger history increases initial work and may use more external resources when all gates allow processing.

### Per-run Limit

Per-run Limit is the maximum number of new videos processed during one Source check.

Example: if eight new videos are waiting and the limit is five, at most five are selected for that run; the remainder stay pending for later work.

Initial History applies to the first look back. Per-run Limit applies to each bounded check. They are not the same control.

### Schedule

Current choices are:

- **Run manually:** no automatic schedule; use Check Now.
- **Daily:** run once per day at the selected local time.
- **Weekly:** run once per week. In rc.3 the UI uses the backend-configured timezone shown on the Source, not a timezone inferred from the browser.

The rc.3 Add Source form does not expose a weekday picker for Weekly; it uses the stored product default. Treat this as a current limitation when choosing Weekly.

Editing a schedule changes future checks. It does not immediately run the Source or replay every missed occurrence. Disabling the automatic schedule preserves past results.

For first-day evaluation, Manual is safer because you can review result quality and Resource Usage before enabling recurring work. The rc.3 Add Source default is an enabled Daily schedule, so review this field before saving.

### Focus

Focus is a comma-separated list of simple terms that help automatic relevance selection prefer videos about subjects you care about.

Good examples:

- `inference, agents, evaluation`
- `pricing, product launch, adoption`
- `database reliability, incident review`

Use specific subjects, not long instructions. Start with one to three terms.

### Ignore

Ignore is a comma-separated list of terms used to exclude videos from automatic relevance selection.

Examples:

- `giveaway, shorts`
- `livestream replay`

Use Ignore sparingly. A broad word can remove useful videos. A skipped video remains visible in Source detail when the product has a record of it.

### Distillation Style

Distillation Style changes the emphasis and ordering of the Intelligence; it does not change the source or trust requirements.

- **Balanced:** mix product, technical, and trend context.
- **Technical:** lead with implementation details and trade-offs.
- **Product case:** lead with product implications and use cases.
- **Trend and opinion:** lead with wider trends and attributed viewpoints.

Balanced is the safest starter choice.

### Check Now

Check Now requests one bounded Source check through the existing safe path. It is separate from adding or editing a Source and is not a retry action.

Possible outcomes include:

- accepted and waiting;
- processing;
- completed with new or updated Intelligence;
- completed with no relevant videos or no important change;
- blocked before provider use;
- failed safely with Source configuration and existing Intelligence unchanged;
- Needs Attention.

Do not repeatedly select Check Now when a run is already pending. rc.3 does not always show a precise processing-time estimate.

### Skipped Videos

A recent video can be marked Skipped when it does not meet automatic relevance criteria, matches Ignore, lacks a usable prerequisite, or is not selected in the current bounded work.

Read the reason shown under the video. “Skipped” does not mean the video was deleted from YouTube or that the channel is disabled.

### Analyze this Video

Use Analyze this Video when a recorded video was skipped for relevance but you intentionally want it considered.

This action overrides **relevance only**. It does not bypass:

- trusted Evidence requirements;
- provider/model scope and availability;
- credential availability;
- budget limits;
- safety or privacy gates;
- terminal unconfirmed-outcome behavior.

The video can still be blocked or fail after the relevance override. Look at Source Run status and Needs Attention for the durable result.

## 6. Intelligence

Open Intelligence for the full current feed. The Saved and Weekly tabs are also located here.

### Conclusion

The concise main finding. It should be understandable without reading implementation details.

### Why this matters

The reason the finding may be relevant to the user or their chosen Focus. This is a relevance explanation, not proof.

### What is new

The new information, change, or information gain relative to the product’s current understanding. If this is vague or repeats the Conclusion, verify the Evidence before treating it as useful.

### Important details

Qualifications, scope, limitations, or context needed to avoid over-reading the Conclusion.

### Claim type

The nature of the statement: Fact, Supported statement, Opinion, Prediction, Rumor, or System inference. See the next section.

### State

State describes the item’s lifecycle, not truth:

- **New:** newly admitted current Intelligence.
- **Updated:** the current understanding changed.
- **Unavailable:** the product cannot safely show the trusted current content.

Other contextual states may appear in history or attention surfaces.

### Evidence

The Source, video, timestamp, and excerpt that support traceability. Use it for important decisions.

## 7. Claim Types

Claim type helps you interpret a statement. It does not remove the need to inspect evidence.

### Fact

A concrete event or property presented as factual in the source and admitted under current trust rules.

Example: “The product announcement lists a public release date of October 12.”

This means the cited source supports that factual statement. It does not guarantee that circumstances never changed afterward.

### Supported statement

A statement supported by the cited video Evidence but better understood as an explanation, interpretation, or bounded technical statement than a standalone fact.

Example: “Batching requests can improve accelerator utilization when workloads are similar.”

### Opinion

An attributed judgment, preference, or evaluation from a person or source.

Example: “The presenter considers the new interface easier for first-time users.”

Do not remove the attribution when sharing an opinion.

### Prediction

A statement about what may happen later.

Example: “The analyst expects smaller on-device models to become more common next year.”

A prediction can be evidence-linked and still turn out to be wrong.

### Rumor

An unconfirmed report or claim described by the source as uncertain.

Example: “Several unnamed suppliers are rumored to be preparing a compatible device.”

Treat a rumor as unverified even when it is accurately quoted from a video.

### System inference

An interpretation produced by the product from admitted information rather than a direct claim by the speaker.

Example: “The system infers that the two announcements may target different customer segments.”

Verify the cited inputs and treat the inference as analysis, not a source quote.

## 8. Evidence

Evidence exists so the compressed Intelligence can be checked against its source.

### Source

The monitored YouTube channel or video. **Open Source** opens the original Source when a safe URL is available.

### Video

The original video title. A video can support more than one Intelligence item, and an Intelligence item should remain tied to its own evidence set.

### Timestamp

The relevant time range. Selecting the timestamp opens the video near the beginning of that range.

### Excerpt

A bounded transcript excerpt that shows the local context. It may be shorter than the surrounding discussion; use the timestamp to inspect context when the claim is important.

### Open Source

Use this external link to view the original public YouTube location. Availability can change outside the product.

### Technical provenance

An advanced disclosure with evidence, Source, revision, or video identifiers. It is useful for diagnostics and audit, but opaque identifiers are not a substitute for the readable Source/video/timestamp path.

### Why Evidence matters

AI can summarize incorrectly or remove nuance. Claim kind and Evidence help you notice attribution, prediction, uncertainty, and scope. For important decisions, read the excerpt and open the video.

## 9. Topics

Open Topics to return to subjects that evolve across Intelligence items.

### Current understanding

The product’s current trusted summary state for the Topic. It can be incomplete or unavailable.

### Updates and timeline

The timeline records changes rather than silently replacing all history. rc.3 may show only a state-level event instead of a full explanation of what changed.

### Disagreement

“Sources still disagree” means the product has not resolved competing information into one conclusion. It is not an error and should not be hidden.

### Uncertainty

The product may say it cannot determine how independent supporting sources are. Repetition across dependent sources is not the same as independent confirmation.

### Evidence and related Topics

Topic contributions should come from current trusted Intelligence. If support is unavailable, the Topic fails closed instead of exposing stale detail. Related Topics may be empty in rc.3.

### Pin Topic

Pinning is the current follow-like action. It marks the Topic for easier return; it does not change source evidence or settle disagreement. In rc.3, Pin may return you to the Topics list.

## 10. Saved

Use Save for Intelligence you want in a personal reference list.

### What Save means

Save is closest to a bookmark/reference. It is not a separate permanent knowledge base and does not make the content immune to later trust changes.

### Save and Unsave

Select Save on an Intelligence card. Open **Intelligence → Saved** to find it. Select Unsave to remove your reference.

### When trusted content becomes unavailable

The saved reference remains so you know something was saved, but the product does not display the old trusted content as if it were still current. This fail-closed behavior is intentional. There is no stale fallback.

## 11. Weekly

Weekly is intended to answer “What mattered this week?” rather than list every video checked.

It can contain:

- one or more important conclusions;
- associated Topics;
- claim and lifecycle states;
- evidence references;
- a correction notice when later trusted Intelligence supersedes a historical item.

### No important changes

If the product says there were no important changes, that is a valid result. It means the available trusted material did not justify a meaningful weekly update. Do not interpret it as proof that no videos were checked.

### Historical corrections

A corrected notice preserves the historical Weekly snapshot while telling you that a later trusted revision should be used for current understanding. Verify the current Intelligence and its Evidence.

## 12. Needs Attention

Needs Attention should be read in four parts: what happened, why it matters, what you can do, and what the system will not do.

### Model unavailable

Video analysis is paused because the approved model path is not available. Existing Sources and Intelligence remain unchanged.

What to do: check Settings for Video Distillation availability or ask the operator to restore the authorized production composition.

What the system will not do: switch to an unqualified model or enable Deep Analysis.

### Credential unavailable

The approved provider credential is not available to the production process.

What to do: ask the local operator to provision the `NVIDIA_API_KEY` indirectly and restart the approved production process if required. Do not paste the key into the UI.

What the system will not do: call the provider without the credential, display its value, or fall back to another provider.

### Provider unavailable

The provider/model endpoint cannot currently be used or is not reported available.

What to do: wait for provider availability and check the Source later. Review the status before starting new work.

What the system will not do: silently change provider or model.

### Budget blocked

The next external operation is not allowed by the available budget.

What to do: review Settings → Resource Usage and the operator-approved budget. A budget change is an explicit operator decision.

What the system will not do: spend beyond the gate or use unknown cost as proof of free usage.

### External result could not be confirmed

The system cannot determine whether an external request completed successfully. Repeating it might duplicate work or cost.

What to do: review the Source status and Resource Usage. Escalate to the operator if a decision is required.

What the system will not do: automatically retry or redispatch the same uncertain work. The UI should not offer Retry for this state.

### Decision required

The system needs an explicit user decision, commonly about Source configuration or an unresolved execution condition.

What to do: open the named Source, review settings and the message, and make only the requested decision.

What the system will not do: guess consent or weaken the blocked rule.

## 13. Settings

Settings contains preferences, Source defaults, model readiness, Resource Usage, and privacy information.

### Provider and model

A **provider** is the external service that runs the approved AI model. A **model** is the specific AI system used for the task.

Current supported tuple:

- Provider: NVIDIA NIM
- Model: `moonshotai/kimi-k3`
- Scope: V1 Video Distillation only
- Available: yes under the current product authority
- Qualified and authorized: yes for this exact scope

Different providers, different models, and different capability scopes are not automatic alternatives.

### Video Distillation

Video Distillation turns relevant, evidence-bounded video information into the Intelligence card structure. It is the only current production-eligible model capability.

### Deep Analysis

Deep Analysis is unavailable. The current Kimi model is not authorized for it, and Settings cannot enable it.

### Cloud and spending behavior

Production eligibility does not mean every Source check makes a cloud call. The product must still pass source relevance, trusted input, credential, budget, and current execution-state gates. When a call is made, it can consume external resources and may have a cost.

### Resource Usage

Resource Usage shows recorded calls, token counts when available, duration when available, cost when available, status, and optional provider/model details. rc.3 entries may be difficult to distinguish because date and Source context are limited.

### Preference Center

Preferences may be:

- **Explicit:** directly chosen by you;
- **Derived:** inferred from feedback;
- **Temporary:** used only until an expiry.

Preferences can influence relevance but do not override source trust or provider gates.

## 14. Costs and Resource Usage

### Calls

Invocation count is the number of recorded external model calls for that execution record. A Source check can do local or skipped work without making a provider call.

### Tokens

Input and output token values appear only when the provider/runtime returned and admitted them. Unavailable token usage must not be guessed.

### Duration

Duration is recorded only when available under the current execution record. A missing duration is not proof of an instantaneous call.

### Cost availability

Cost can be unavailable even when a call occurred. **UNKNOWN or Unavailable cost does not mean zero or free.** Do not infer a price from token counts unless a separately authoritative pricing source and calculation policy are in place.

### Reading Resource Usage safely

Use status and actual provider/model details where present. Because rc.3 may label multiple entries simply as “Recorded work,” keep your own operational note if you need to reconcile an important manual run.

## 15. Privacy and Data Handling

### Local-first behavior

The product persists its workspace locally by default, including its local database and approved product artifacts. Local-first does not mean “no network use”: YouTube access and approved NVIDIA model processing are external operations when used.

### External model input

For V1 Video Distillation, the external model receives the minimum approved, evidence-bounded distillation input. The full transcript is not sent by default. The input is tied to approved Evidence and is subject to the current provider/model/budget/trust gates.

### Credentials

Credential values are supplied indirectly at runtime and are not shown by the UI. Do not place credentials in Source URLs, Focus/Ignore terms, screenshots, logs, tracked configuration, or documentation.

### What is not claimed

This manual does not claim end-to-end anonymity, provider-side deletion, encryption guarantees, zero retention by external services, or protection beyond the product’s implemented controls. Review the external provider’s applicable terms and your operator’s data policy before using sensitive material.

## 16. Common Workflows

### Follow a technology channel

1. Add the channel as a Source.
2. Use Balanced or Technical style.
3. Add two or three Focus terms such as `inference, evaluation, agents`.
4. Start with Initial History 5 and Per-run Limit 5.
5. Run manually and verify a technical claim at its timestamp.
6. Enable a Daily or Weekly schedule only after checking signal quality and Resource Usage.

### Follow a product or industry channel

1. Add the channel.
2. Use Product case or Trend and opinion style.
3. Use Focus such as `launch, pricing, adoption`.
4. Keep Ignore blank until you observe repeat noise.
5. Treat forecasts and presenter judgments as Prediction or Opinion, not Fact.

### Track a Topic over time

1. Open Topics after related Intelligence exists.
2. Read Current understanding and uncertainty.
3. Inspect available contributions and timeline.
4. Pin the Topic if you want to return.
5. When sources disagree, open the underlying Intelligence/Evidence instead of assuming consensus.

### Check a Source manually

1. Open Sources and select the Source.
2. Confirm monitoring/policy and current Source Run status.
3. Select Check Now once.
4. Wait for a durable result or Needs Attention.
5. Review recent videos and new Intelligence.

### Verify an important claim

1. Read the claim type and Important details.
2. Confirm the Source and video.
3. Open the timestamp.
4. Compare the excerpt with the surrounding video context.
5. If the claim is Opinion, Prediction, Rumor, or System inference, preserve that label when using it elsewhere.

### Review your week

1. Open Intelligence → Weekly or use the Dashboard link.
2. Read the week-level conclusion and what changed.
3. Note any correction or unavailable evidence.
4. Open current Intelligence and Evidence for decisions that still matter.
5. Accept “no important changes” without manufacturing activity.

## 17. Troubleshooting

### No Intelligence generated

Check, in order:

1. Is the Source enabled?
2. Is there a completed or blocked Source Run?
3. Were there new or initially selected videos?
4. Did Focus/Ignore make them irrelevant?
5. Was trusted transcript/Evidence available?
6. Is Video Distillation available in Settings?
7. Is the credential available to the production process?
8. Is budget available?
9. Is the UI running the standard guarded `serve-api` composition rather than a production executor?

A completed run with no important change is valid.

### Source skipped

Read the reason in Recent videos. Adjust Focus/Ignore for future automatic selection only if the rule is genuinely wrong. Use Analyze this Video for a deliberate relevance override; other gates still apply.

### Model unavailable

Open Settings and confirm the exact NVIDIA NIM / Kimi Video Distillation capability. The product will not substitute another model. Ask the operator to restore the authorized production composition.

### Credential missing

The UI cannot accept the credential. The operator must make `NVIDIA_API_KEY` available indirectly to the approved process. Never expose its value while diagnosing.

### Budget reached

Open Resource Usage, identify the relevant work where possible, and obtain an explicit operator decision before increasing budget or starting more external work.

### External result could not be confirmed

Do not retry the same uncertain operation. The product preserves this terminal state to avoid duplicate work or spend. Review status and escalate to the operator.

### Evidence unavailable

The product may be unable to safely read current evidence or the external video may be gone. It should not invent an excerpt or substitute unrelated evidence. Treat the Intelligence as unavailable until trusted Evidence is restored through an authorized path.

### Saved item unavailable

The reference remains, but stale detail is not shown. This is intentional. Unsave the reference if you no longer need it; do not rely on a copied stale conclusion as current truth.

### UI does not start

- Confirm the local API process is running.
- Confirm the frontend points to the same API port through `YIA_API_BASE`.
- If a port is already occupied, do not terminate an unknown process blindly. Identify the existing local service, reuse the correct running instance, or choose an approved unused loopback port and keep the API/frontend values consistent.
- Run `youtube-intel doctor` for read-only local prerequisite information.

### LIMITATION / NEEDS PRODUCT CLARIFICATION

rc.3 does not package the confirmed normal-production Source execution composition as one supported ordinary-user launch command. Product Owner/operator guidance is required to distinguish a guarded review UI from a production-ready local workspace.

## 18. What the Product Does Not Currently Support

- Deep Analysis.
- Usable Investigations, external evidence expansion, or external validation workflows.
- A browser-based credential setup flow.
- Automatic provider or model fallback.
- Automatic retry of an unconfirmed external result.
- A general end-user one-command production UI launcher.
- A full mobile application or a formally certified mobile layout.
- V2 functionality; rc.3 contains only the V1 behavior described in this manual.
- Later-generation strategic capabilities sometimes discussed outside this manual; if a feature is not described here as current, assume it is unavailable in rc.3.

The Investigations navigation item is present but explicitly unavailable. Do not interpret its presence as a usable feature.

## 19. Best Practices

### Start with few Sources

Begin with one to three channels whose content you already understand. This makes it easier to measure relevance, novelty, and trust before information accumulates.

### Keep Per-run Limits reasonable

Five is a practical starter limit. Increase only after you understand backlog behavior, processing time, and Resource Usage.

### Use Focus and Ignore as filters, not instructions

Use short concrete terms. Review skipped videos before broadening Ignore. Do not place private instructions, credentials, or sensitive data in these fields.

### Use Check Now intentionally

Use it for first setup, an urgent channel update, or after a deliberate configuration change. Do not use repeated clicks as a retry mechanism.

### Read Evidence proportionally to risk

Scan Evidence for routine learning. Open the timestamp and surrounding video for important product, financial, legal, safety, or public claims. This product does not replace professional judgment.

### Preserve uncertainty

When sharing Intelligence, keep Opinion, Prediction, Rumor, and System inference labels. Do not turn one source’s supported statement into multi-source consensus.

### Review recurring use

After several days, use Dashboard for orientation, Weekly for catch-up, Topics for evolving subjects, Saved for personal references, and Needs Attention for blockers. Periodically remove low-value Sources or narrow their Focus rather than increasing processing volume.

## 20. Glossary

| Term | Plain-language meaning |
| --- | --- |
| Analyze this Video | consider a video despite a relevance skip; all other restrictions remain |
| Check Now | request one bounded Source check through the safe path; not a retry command |
| Claim type | the nature of a statement, such as Fact, Opinion, or Prediction |
| Conclusion | the main finding in an Intelligence card |
| Deep Analysis | an unavailable capability in rc.3 |
| Distillation | turning approved, evidence-bounded video information into concise Intelligence |
| Evidence | Source, video, timestamp, and excerpt used to trace a claim |
| Fact | a concrete factual statement supported as such by the cited source and current trust rules |
| Focus | terms that help automatic relevance selection prefer certain subjects |
| Ignore | terms that exclude videos from automatic relevance selection |
| Initial History | number of recent existing videos considered when a Source is first added |
| Intelligence | a concise, evidence-linked finding produced from relevant video information |
| Model | the specific AI system used for an approved task |
| Needs Attention | a safe block or decision state that requires user/operator review |
| New | lifecycle state meaning newly admitted, not “more true” |
| Opinion | an attributed judgment or preference |
| Per-run Limit | maximum new videos processed in one Source check |
| Pin Topic | current action for marking a Topic for easier return |
| Prediction | a statement about what may happen later |
| Provider | the external service that runs the approved model; currently NVIDIA NIM for V1 Video Distillation |
| Resource Usage | recorded calls, tokens, duration, cost availability, and provider/model detail |
| Rumor | an unconfirmed report represented as uncertain |
| Save / Saved | add/remove an Intelligence reference in your personal list |
| Source | a monitored YouTube channel or supported video |
| Source check | one bounded attempt to discover/select/process work for a Source; the UI may also say Source Run in technical detail |
| Supported statement | a statement supported by the cited video Evidence but not necessarily a standalone universally verified fact |
| System inference | an interpretation produced by the product rather than a direct source statement |
| Technical provenance | advanced diagnostic identifiers that record where trusted content came from |
| Topic | an evolving current understanding built from trusted Intelligence |
| Updated | lifecycle state meaning the current Intelligence changed |
| Weekly | historical summary of what mattered during a week |

## Manual Accuracy Note

This manual intentionally does not describe planned features, internal task identifiers, unavailable Deep Analysis behavior, or unimplemented investigation actions. Where the installed UI and normal-production capability are not connected by a packaged user workflow, the limitation is stated rather than invented.
