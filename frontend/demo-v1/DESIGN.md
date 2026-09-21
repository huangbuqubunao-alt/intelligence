---
version: v1-pre-freeze-prototype
name: Intelligence V1 Pre-freeze Demo
description: A restrained, evidence-first knowledge workspace with scalable Following Focus and content-level Video Notes.
colors:
  primary: "#56C98E"
  page: "#0B0E13"
  surface: "#10151C"
  surface-raised: "#151B24"
  border: "#232C38"
  border-strong: "#303B49"
  text-primary: "#F3F5F2"
  text-secondary: "#C2C9C4"
  text-muted: "#89938F"
  accent-soft: "#10251C"
  error: "#EE948E"
typography:
  display:
    fontFamily: Inter, PingFang SC, sans-serif
    fontSize: 56px
    fontWeight: 590
    lineHeight: 1.08
    letterSpacing: -0.04em
  heading:
    fontFamily: Inter, PingFang SC, sans-serif
    fontSize: 24px
    fontWeight: 580
    lineHeight: 1.25
    letterSpacing: -0.02em
  body:
    fontFamily: Inter, PingFang SC, sans-serif
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.7
  evidence:
    fontFamily: Songti SC, serif
    fontSize: 17px
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: Inter, PingFang SC, sans-serif
    fontSize: 11px
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: 0.14em
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  section: 48px
  page: 56px
rounded:
  sm: 6px
  md: 10px
  lg: 14px
  full: 9999px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#06120C"
    rounded: "{rounded.sm}"
    height: 40px
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    padding: 24px
  card-muted-copy:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.md}"
  app-shell:
    backgroundColor: "{colors.page}"
    textColor: "{colors.text-primary}"
  navigation:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-muted}"
  input:
    backgroundColor: "{colors.page}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.sm}"
    height: 44px
  focus-indicator:
    backgroundColor: "{colors.border-strong}"
    size: 2px
  divider:
    backgroundColor: "{colors.border}"
    height: 1px
  evidence-panel:
    backgroundColor: "#0D1218"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    padding: 22px
  verified-context:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.text-primary}"
  error-state:
    backgroundColor: "#2B1617"
    textColor: "{colors.error}"
---

# Intelligence V1 Pre-freeze Demo Design System

## Overview

The UI is a professional, restrained multi-source knowledge workspace. Intelligence remains the primary long-term judgment object; Evidence, Following, and Content form its immediate context; processing and health are quiet supporting layers. The pre-freeze polish adds scalable Following organization and content-level Video Notes without changing the Hybrid visual direction, six-item navigation, or knowledge chain.

## Colors

Near-black tonal surfaces replace dashboard chrome. A single evidence green identifies primary actions, links, verified context, and selected states. Muted slate carries metadata. Red and amber are reserved for actionable failure and uncertainty, and always appear with explanatory text.

## Typography

System sans-serif typography supports dense Chinese and English UI without external font requests. Large headings use restrained weight and tight tracking. Original Evidence excerpts use the local Songti serif stack to distinguish quoted source material from AI interpretation without adding decoration.

## Layout

Desktop uses a 224px persistent navigation rail and a fluid content column capped at 1180px. The base rhythm is 4px, with 16px component grouping, 24px card padding, and 48px section separation. Dashboard reads top-to-bottom as a brief. Intelligence Detail uses a bounded main-plus-evidence layout. At 980px, Evidence moves below the claim and loses sticky/max-height behavior.

## Elevation & Depth

Depth comes from tonal layers and hairline borders, not stacked shadows. Only onboarding and modal/drawer surfaces receive a shadow because they sit above the application plane.

## Shapes

Containers use 10px radii, evidence context uses 14px, and controls use 6px. Pills are avoided except where a compact selected filter needs containment. Status is expressed with text and a small mark, never color alone.

## Components

- Buttons: one green primary action per decision surface; secondary uses a raised neutral; quiet actions remain text-forward.
- Cards: reserved for cohesive content objects such as an Intelligence, Topic, or state explanation—not every metric.
- Evidence: quote, Provider, Following, content, position, strength, and provenance action remain in one block.
- Forms: visible labels, helper text, 44px controls, explicit error recovery, and a clear note that Demo inputs are not persisted.
- Status: a short title answers what happened; supporting text explains data safety and the next action.
- Navigation: 首页、关注、洞察、主题、调研、设置 appear in the sidebar and collapse to a horizontally scrollable rail on narrow screens.
- Following library: one-layer Groups, light status filters, search, and information-dense rows keep 18+ objects scannable without becoming a card wall.
- Following Focus: default Preferences stay visible first; per-Following focus and processing controls appear only after an explicit override choice.
- Video Notes: Content Detail reads source metadata → summary → key points → chapters → Evidence → Intelligence → Topic → Research.
- Summary boundary: Summary explains what one content says; Intelligence explains which evidence-backed judgment deserves long-term tracking. A complete summary with no Intelligence is a normal success state.
- Empty/loading/error: reviewers can access all secondary states through the Demo-only drawer without allowing them to dominate the product path.
- Model strategy: Level 1 presents four understandable policies; Level 2 maps task groups to model classes; Level 3 diagnostics stay collapsed and outside the normal decision path.
- Knowledge governance: uncertainty, conflicting Evidence, Topic lifecycle, evolution entries, and Research snapshots use explanatory language rather than opaque scores or engineering terms.
- Data trust: backup, restore, corruption protection, and Obsidian publishing clearly state their one-way, local-first semantics.

## Do's and Don'ts

- Do keep Intelligence, Topic, and Research visually dominant over operational state.
- Do preserve Following → Content → Evidence → Intelligence → Topic → Research through breadcrumbs, metadata, grouping, and timelines.
- Do keep Following Groups as user organization and Following Focus as input preference; neither is a Topic alias.
- Do keep Video Notes inside Content Detail and preserve a clear visual boundary before Intelligence.
- Do show “未发现值得长期保留的新洞察” as a successful content-processing result when appropriate.
- Do treat Following as an input entry, never as the owner of a cross-source Intelligence or Topic.
- Do keep Research library-first and make its current or specified scope visible before execution.
- Do explain local-first storage and Obsidian as optional one-way knowledge output.
- Do explain that task complexity selects an eligible model and that cost preferences never bypass minimum quality.
- Do preserve disagreement between supporting, contradicting, and conditional Evidence.
- Do treat Research as a dated snapshot with an Evidence cutoff, never as an overwrite of previous knowledge.
- Do keep model routing progressive: strategy first, task mapping second, diagnostics last.
- Do keep Evidence in the same reading context as the claim and make timestamps actionable.
- Do label every simulated connection or processing action as Demo.
- Don't expose internal admission, dispatch, reservation, qualification, or provider transport language.
- Don't turn Following Groups into folders, taxonomy, or Topic governance.
- Don't imply every generated Summary should become Intelligence.
- Don't use KPI-card rows, decorative gradients, complex node graphs, game mechanics, or a page full of status badges.
- Don't imply a real Provider connection, backend call, credential save, capability change, routing execution, token accounting, SQLite write, backup, restore, file selection, or Obsidian sync.
- Don't present Intelligence as absolute truth, flatten conflicting Evidence, or replace an older Research snapshot.
