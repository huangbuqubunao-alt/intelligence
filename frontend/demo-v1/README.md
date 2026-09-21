# Intelligence — V1 Pre-freeze Demo (Final Revision)

This is a standalone, frontend-only prototype for the final V1 Owner review. It keeps the existing Following → Content → Summary / Notes → Evidence → Intelligence → Topic → Research information architecture and the selected Orbit logo, and adds the two approved final pre-freeze capabilities: **Multilingual Content UX** and **lightweight Global Search**.

Everything is fixture-driven. It does not import the production workspace, call `/api`, invoke a cloud or local model, run real language detection or translation, build a real search index, calculate real token cost, open a file picker, write SQLite, create a backup, restore data, or publish an Obsidian file.

Start the existing Vite server from `frontend/`:

```bash
npm run dev -- --host 127.0.0.1
```

Open:

- First run: `http://127.0.0.1:5173/demo-v1/`
- Direct workspace review: `http://127.0.0.1:5173/demo-v1/?start=workspace`
- Direct screen review: append a hash such as `#following`, `#intelligence-detail-pricing`, `#topic-detail`, `#research`, `#search`, or `#settings` to the workspace URL.

## Language model

Three independent concepts, never conflated:

- **界面语言 (UI language)** — product chrome text. The Demo copy stays 简体中文 as a placeholder; switching it does not change content or generated artifacts.
- **源语言 (Source language)** — intrinsic to each Content / Evidence fixture (e.g. an English YouTube video, an English X post). Source content is always preserved in its original language.
- **内容输出语言 (Content output language)** — the language of generated artifacts (summary, key points, chapters, Intelligence, Topic, Research). A user can follow English sources while reading all outputs in 简体中文.

Evidence adds a display switch — **译文 / 双语 / 原文**. Translation is a reading aid only: the original excerpt + source position stay authoritative, and a translation never creates a second Evidence record. Full transcripts are **not** translated by default; an on-demand `翻译完整字幕` mock is provided to limit model usage. Each Following can optionally override its output language under progressive disclosure.

## Global Search

A compact search trigger in the workspace header opens `搜索你的 Intelligence`. V1 search only **locates existing knowledge** across 关注 / 内容 / 洞察 / 主题 / 调研 / Evidence using fixture, browser-state filtering — no real index, no database, no embeddings, no semantic Q&A, no AI chat answers, no external internet search. Lightweight type filters (全部 / 关注 / 内容 / 洞察 / 主题 / 调研 / Evidence) and a useful no-result state are included. Cross-language discovery is demonstrated through curated fixture tags: a Chinese query surfaces a Chinese Intelligence whose supporting Evidence includes English sources.

## Final pre-freeze owner paths

Multilingual:

- A — English source / Chinese output: `#content-youtube-agent-pricing-en` → English title → 源语言 English → 内容输出语言 简体中文 → Chinese 一句话总结 / 核心要点 / 时间戳章节.
- B — Evidence language: an English-source content → Evidence 显示 → 译文 → 双语 → 原文.
- C — Full transcript: English content → 查看可追溯内容文本 → 翻译完整字幕 → mock translated transcript.
- D — Cross-language Intelligence: `#intelligence-detail-pricing` → English YouTube + Chinese Bilibili + English X → one 简体中文 Intelligence, each Evidence keeps its own source language.
- E — Following override: `#following-practical-ai` → 使用全局语言设置 → 为这个关注单独设置 → English output.

Global Search:

- F — Locate: header 搜索 → `Agent 商业化` → Following + Content + Intelligence + Topic + Research results → click through to the object.
- G — Filter: 全部 → 洞察 → 主题.
- H — Empty: an unknown query → clear no-result state that stays inside the library.

Prior revisions remain available:

- Following scale (关注 → 18 objects → Group → Filter → Search), Following Focus override, Content Summary / Video Notes, summary-without-Intelligence, conflicting Evidence, Topic lifecycle / evolution, Research snapshots, Backup / Restore, Obsidian publishing, model strategy and the review drawer.

All content comes from `src/demo-v1/fixtures.ts`. Search, filters, language settings, default/override settings, transcript translation, timestamp jumps, detailed-summary generation, Provider links, backups, restore checks, and Obsidian publishing are browser-state mocks only. They make no network request and write no persistence.

Research defaults to the local fixture library. “Current object” and “Specified scope” are selectable; external exploration remains disabled. Obsidian is an optional one-way publishing target while Intelligence retains complete local operating data.
