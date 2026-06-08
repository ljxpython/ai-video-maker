---
name: ai-video-maker
description: Use when the user wants AI-assisted video creation through a skills-first workflow for technical, product, tutorial, SOP, repository, API, bug reproduction, or release note videos. Orchestrates brief alignment, plan confirmation, recording, narration, subtitles, editing, QA, revision, packaging, and upload/publish gates.
---

# AI Video Maker Orchestrator

## Core Positioning

This is the user-facing orchestrator skill for AI Video Maker. It implements the `ai-video-orchestrator` role in this repository.

The user should describe the video they want. The assistant should use this skill to align the requirement, propose a plan, ask for gate confirmations, recommend and call the right sub-workflows, and produce a video package.

Do not present the CLI as the main user workflow. The repository harness and CLI are internal execution substrate for skills, debugging, and reproducible runs.

## User-Facing Flow

1. Understand the user's video need.
2. Tell the user the next recommended workflow is `video-brief`.
3. Produce or refine a structured brief.
4. Stop at the `brief` gate and ask for confirmation.
5. Tell the user the next recommended workflow is `video-plan`.
6. Produce storyboard, asset plan, capability plan, and detailed execution steps.
7. Stop at the `plan` gate and ask for confirmation.
8. Tell the user whether the next recommended workflow is `video-script`, `browser-capture`, `voice-subtitle`, or another workflow.
9. If browser, Chrome, or desktop GUI actions are needed, explain the exact action and stop at the `execution` gate.
10. Generate or capture visual assets.
11. Generate narration and subtitles.
12. Edit and render the video.
13. Run QA and route revisions to the right workflow.
14. Prepare the publishing package.
15. Stop at `upload` and `publish` gates before any platform-side action.

At every stage, say clearly:

- What was completed.
- What the user should review.
- Which gate, if any, is required.
- Which skill should be called next if the user approves.
- Which skill should be called for revision if the user rejects the result.

## Sub-Workflow Map

The first child skills are already defined as separate P0 skills. Later workflows may still execute as sections inside this skill until they are split out.

| Workflow | Purpose | Expected Outputs | Gate |
|---|---|---|---|
| `video-brief` | Align requirement, audience, platform, duration, style, constraints | `brief.yml` | `brief` |
| `video-plan` | Build storyboard, asset plan, capability plan, production steps | `plan/storyboard.yml`, `plan/asset_plan.yml`, `plan/capability_plan.yml` | `plan` |
| `video-script` | Write narration, subtitles draft, screen action script | `script/narration.zh.txt`, `script/screen_actions.md` | plan revision if needed |
| `browser-capture` | Inspect, screenshot, or record public/local browser interactions | `assets/browser/*`, `qa/browser_capture.*` | `execution` |
| `terminal-capture` | Run approved safe terminal commands and render output cards | `assets/terminal/*`, `qa/terminal_capture.*` | `execution` |
| `chrome-capture` | Plan or record authenticated Chrome visible-page results | `assets/chrome/*`, `qa/chrome_operation.*` | `execution` |
| `desktop-capture` | Plan or record desktop GUI visible results | `assets/desktop/*`, `qa/desktop_operation.*` | `execution` |
| `voice-subtitle` | Generate AI voice and subtitles | `audio/narration.mp3`, `subtitles/captions.srt` | none unless revision |
| `edit-render` | Compose, edit, and render final horizontal/vertical videos | `render/final_16x9.mp4`, `render/final_9x16.mp4` | none unless revision |
| `qa-revision` | Verify video quality and route fixes | `qa/report.md`, `qa/issues.yml` | revision confirmation if needed |
| `publish-package` | Prepare video, thumbnail, chapters, metadata, upload checklist | `package/*` | `upload`, `publish` |
| `youtube-upload` | Prepare YouTube upload plan and dry-run; gated real upload/publish entry | `upload/*` | `upload`, `publish` |

## Review Model

There are two review types:

| Review Type | Meaning | Examples |
|---|---|---|
| Hard gate | Must wait for explicit user confirmation before continuing | `brief`, `plan`, `execution`, `upload`, `publish` |
| Soft review | Show results and next recommendation; user may continue or request revision | script, voice, subtitles, render, QA, package metadata |

Do not ask for hard-gate confirmation at every tiny step. Use hard gates only for product direction, execution risk, account-side effects, upload, and publish.

## Gate Policy

Never skip these confirmations:

- `brief`: video goal, audience, platform, style, duration, constraints.
- `plan`: chapter structure, visual plan, narration direction, execution steps.
- `execution`: browser, Chrome login state, desktop GUI, local file picker, screen recording, or account-affecting preparation.
- `upload`: uploading files to a third-party platform.
- `publish`: making the video public, unlisted, scheduled, or otherwise published.

Ask close to the side-effect. Prepare safe files and metadata first, then ask before the account or external-platform action.

## Capability Policy

Prefer scripted or API-based execution when it can complete the task reproducibly.

Use GUI capabilities only when the workflow needs real UI interaction:

| Capability | Use When | Avoid When |
|---|---|---|
| `$browser` | Local web demos, public webpages, DOM checks, screenshots, browser recording | Existing user login state is required |
| `$chrome` | Existing Chrome login state is required, such as YouTube Studio or authenticated dashboards | Cookies, passwords, or session secrets would need inspection |
| `$computer-use` | Desktop apps, OBS, editors, file pickers, native dialogs | CLI/API/scripted execution is enough |

## Handoff Contract

After each workflow, return or persist a handoff block. The orchestrator uses it to decide what to show the user and which skill to call next.

```yaml
skill: video-plan
run_id: demo
status: ready_for_gate
outputs:
  - plan/storyboard.yml
  - plan/asset_plan.yml
  - plan/capability_plan.yml
review_checklist:
  - Confirm chapter structure
  - Confirm narration direction
  - Confirm browser capture scope
risks:
  - browser capture requires execution approval
next_gate: plan
next_skill_suggestion: video-script
revision_skill_suggestion: video-plan
user_action_required: true
user_message: "Please review the storyboard, asset plan, and execution steps. If approved, the next recommended skill is video-script."
```

Required fields:

- `skill`
- `run_id`
- `status`
- `outputs`
- `review_checklist`
- `risks`
- `next_gate` when confirmation is needed
- `next_skill_suggestion` when the next workflow is clear
- `revision_skill_suggestion` when the likely revision target is clear
- `user_action_required`
- `user_message`

Supported `status` values:

- `ready_for_gate`
- `ready_for_review`
- `done`
- `needs_revision`
- `blocked`

## Orchestrator Decision Rules

Use the handoff block this way:

| Status | Action |
|---|---|
| `ready_for_gate` | Show outputs, risks, review checklist, and ask for explicit confirmation |
| `ready_for_review` | Show outputs and checklist; allow the user to continue or request revision |
| `done` | Summarize completed outputs and recommend `next_skill_suggestion` |
| `needs_revision` | Explain what failed and route to `revision_skill_suggestion` |
| `blocked` | Ask only for the missing information needed to unblock |

If the user says "continue" after a soft review, proceed to `next_skill_suggestion`.

If the user asks for changes, route to `revision_skill_suggestion` or the most relevant earlier workflow.

## Internal Harness Use

When working inside this repository, use the harness to keep state reproducible.

Typical internal actions:

```bash
ai-video-maker validate --pipeline pipeline.example.yml
ai-video-maker run --pipeline pipeline.example.yml --run-id <run_id> --overwrite
ai-video-maker approve --run runs/<run_id> --gate brief --summary "<summary>"
ai-video-maker run --run runs/<run_id>
ai-video-maker approve --run runs/<run_id> --gate plan --summary "<summary>"
ai-video-maker status --run runs/<run_id>
```

These commands are for the assistant or developer. Do not make the user manually run them unless the user is debugging or explicitly asks for CLI usage.

## Output Shape

A complete run should produce:

```text
runs/<run_id>/
  brief.yml
  approvals.yml
  state.json
  artifacts.yml
  plan/storyboard.yml
  plan/asset_plan.yml
  plan/capability_plan.yml
  script/narration.zh.txt
  subtitles/captions.srt
  audio/narration.mp3
  render/final_16x9.mp4
  qa/report.md
  package/video.mp4
  package/title.txt
  package/description.md
  package/tags.txt
  package/upload_checklist.md
```

## Quality Bar

- The first 10 seconds must explain value or show the result.
- Every narration section must map to a visual.
- Commands and UI actions must be verified before recording.
- Subtitles must not cover important UI.
- Final video must contain both audio and video streams.
- QA must include duration, resolution, codec, audio stream, subtitle readability, and keyframe checks.
