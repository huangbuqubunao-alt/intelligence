# YouTube Intelligence Agent — Quick Start

This guide is for v0.1.0-rc.3. It aims to get you from an already installed, production-ready local workspace to useful Intelligence in about 5–10 minutes of active setup. Video discovery and AI processing can take additional time.

For every important conclusion, the original video remains the source of truth: information can be compressed, but the source must remain reachable.

## What This Product Does

YouTube Intelligence Agent watches the YouTube Sources you choose, looks for relevant videos, and turns meaningful information into concise, evidence-linked Intelligence.

Instead of giving you another video queue, it helps answer:

- What did I learn?
- Why does it matter to me?
- What is actually new?
- Is this a fact, opinion, prediction, rumor, or system inference?
- Where in the original video did it come from?

In rc.3, external AI processing is limited to Video Distillation using NVIDIA NIM and `moonshotai/kimi-k3`. Deep Analysis and Investigations are not available.

## Before You Start

You need:

- a private rc.3 installation and its local data workspace;
- a YouTube channel, handle, or supported video URL;
- the local API and web interface running;
- NVIDIA NIM / `moonshotai/kimi-k3` shown as available for Video Distillation;
- an NVIDIA credential supplied indirectly to the production process;
- available usage budget.

The product does not show, store, or accept an API key in the browser. The validated runtime credential name is `NVIDIA_API_KEY`; an operator must make it available to the production process without printing it or saving it in the repository.

> **Current rc.3 startup limitation:** the repository-supported `youtube-intel serve-api` command starts the loopback UI API but does not, by itself, wire in the normal-production Source executor. In that standard composition, **Check Now is safely blocked**. A normal-production Source Run for rc.3 has been confirmed, but the corresponding ordinary-user one-command launcher is not packaged in this tag. If you are not the installer/operator, ask for a local URL whose Source execution and credential readiness have already been configured.

## 1. Start the Product

If an operator has already started your workspace, open the local URL they provide, normally a `127.0.0.1` address. The browser interface should show Dashboard, Intelligence, Topics, Sources, Investigations, and Settings.

For the repository-supported loopback interface, an installer can run the following from the repository root after installation and local configuration:

```sh
youtube-intel serve-api --database /absolute/path/to/state.sqlite3 --port 8765
```

In a second terminal:

```sh
YIA_API_BASE=http://127.0.0.1:8765 npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
```

Then open `http://127.0.0.1:5173/`.

These commands expose the product only on the local computer. They do not solve the rc.3 production-executor limitation described above.

Before adding a Source, open **Settings** and confirm:

- Video Distillation is available;
- the provider is NVIDIA NIM;
- the model is `moonshotai/kimi-k3`;
- the scope is Video Distillation only;
- Deep Analysis says Unavailable.

Settings never displays the credential value.

## 2. Add Your First Source

A **Source** is a YouTube channel or supported individual video that you want the product to monitor.

1. Open **Sources**.
2. Select **Add Source**.
3. Paste the YouTube channel, handle, or supported video URL.
4. Keep **Turn relevant videos into Intelligence** selected.
5. Keep **Monitor this Source** on if you want future checks.

Choose one Source with recent videos on a subject you understand well. That makes it easier to judge whether the first Intelligence is useful and accurately linked to the video.

## 3. Choose Simple Starter Settings

Use these settings for a first Source:

| Setting | Starter choice | What it means |
| --- | --- | --- |
| Initial history | 5 recent videos | Consider up to five recent existing videos when the Source is first added |
| Per-run limit | 5 new videos | Process at most five new videos in one check; overflow remains pending |
| Focus | 1–3 concrete terms, or blank | Prefer videos related to these terms |
| Ignore | Blank at first | Automatically exclude videos matching these terms later if needed |
| Distillation style | Balanced | Mix product, technical, and trend context |
| Schedule | Manual for the first day | Prevent recurring checks until you have reviewed the first result |

Examples:

- Technology channel Focus: `language models, inference, agents`
- Product/industry channel Focus: `launch, pricing, adoption`
- Ignore only when the pattern is obvious: `shorts, giveaway, livestream replay`

Focus and Ignore affect automatic relevance selection. They do not change the original video or bypass trust rules.

**Advanced:** Initial history, Per-run limit, filters, style, and schedule are useful controls, but none is a quality guarantee. Start small and adjust after you see what is selected.

Save the Source. Adding it does not itself prove that a video was processed.

## 4. Run It Now

Open the Source and select **Check Now**.

Check Now asks the product to look for work through the normal safe Source-check path. It is not a retry command. Depending on the current state, you may see:

- waiting or processing;
- complete, possibly with new Intelligence;
- no relevant videos or no important change;
- Needs Attention because a credential, model, provider, budget, or decision is unavailable;
- a safe execution block in the standard rc.3 loopback composition.

You can leave the Source page while processing continues, but rc.3 does not always provide a reliable time estimate. Do not repeatedly press Check Now to force progress.

## 5. Read Your First Intelligence

Open **Dashboard** or **Intelligence**. Read each card in this order:

1. **Conclusion** — the main thing learned.
2. **Why this matters** — why the item may be relevant to you.
3. **What is new** — the information gain or change.
4. **Important details** — qualifications and supporting context.
5. **Claim type** — Fact, Supported statement, Opinion, Prediction, Rumor, or System inference.
6. **State** — for example, New, Updated, or Unavailable.
7. **Evidence** — Source, video, timestamp, and excerpt.

Treat a claim label as guidance about the nature of the statement, not as a replacement for checking important evidence.

## 6. Verify the Source

In the card’s **Evidence** section:

1. confirm the Source name;
2. confirm the video title;
3. select the timestamp to open the original video at that point;
4. compare the transcript excerpt with the conclusion;
5. use **Open Source** if you want to inspect the original channel or video.

Technical provenance is optional diagnostic detail. The normal verification path is Source → video → timestamp → excerpt.

## 7. Save or Follow a Topic

Select **Save** when you want an Intelligence item in your personal reference list. Open **Intelligence → Saved** to return to it.

Saved is a reference, not a stale copy of truth. If the current trusted content later becomes unavailable, the product keeps the saved reference but does not show old detail as if it were current. You can then Unsave it.

Open a **Topic** to see its current understanding and history. rc.3 calls the follow-like action **Pin Topic**. Pinning makes the Topic easier to return to; it does not resolve disagreement or guarantee updates.

## 8. What to Do If Nothing Appears

Common reasons include:

- the Source has no new videos;
- recent videos did not match Focus or matched Ignore;
- subtitles or trusted Evidence were unavailable;
- no change was important enough to create Intelligence;
- the Source check is still waiting or processing;
- Video Distillation, the credential, provider, or budget is unavailable;
- the standard rc.3 loopback UI is running without a production Source executor.

Check the Source’s recent videos and Source Run status, then look for **Needs Attention**. A truthful “no important change” is a valid result and is better than filler.

## 9. Needs Attention

Needs Attention does not mean your existing Intelligence was deleted.

- **Model or credential unavailable:** processing is paused. Check Settings or ask the local operator to restore readiness.
- **Provider unavailable:** wait for the provider to be available; the product does not silently switch provider or model.
- **Budget blocked:** review Resource Usage and the approved budget before another check.
- **External result unconfirmed:** the product will not automatically retry because doing so could duplicate work or cost.
- **Decision required:** open the named Source and review its configuration.

Never paste an API key into a Source field, Focus/Ignore field, browser storage, or support screenshot.

## 10. Recommended First-Day Setup

Try this bounded setup:

- one YouTube channel you trust;
- Initial history: 5 recent videos;
- Per-run limit: 5 new videos;
- Focus: two or three specific topics;
- Ignore: blank;
- Distillation style: Balanced;
- Schedule: Manual;
- run Check Now once;
- verify at least one conclusion against its timestamp and excerpt;
- Save one useful item;
- only then change the schedule to Daily or Weekly if the result quality and resource use are acceptable.

Once this works, continue to the [full user manual](RC3_USER_MANUAL.md).
