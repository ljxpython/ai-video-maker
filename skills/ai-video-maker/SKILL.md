---
name: ai-video-maker
description: Use when the user wants AI-assisted video creation for technical, product, tutorial, SOP, repository, API, bug reproduction, or release note videos. Covers brief alignment, planning, recording, narration, subtitles, editing, QA, packaging, and upload preparation.
---

# AI Video Maker Skill

## Core Principle

The user gives a video need. The assistant turns it into an aligned plan, asks for confirmation at the right gates, then uses the available tools to produce a video package.

Do not assume this skill is only for repository explainer videos. Repository explanation is one scenario. The broader target is structured demo and explanation videos.

## Workflow

1. Align the brief.
2. Propose a video plan.
3. Ask the user to confirm the plan.
4. Produce detailed execution steps.
5. Ask the user to confirm execution.
6. Capture assets with available capabilities.
7. Generate narration and subtitles.
8. Render and auto-edit the video.
9. Run QA.
10. Prepare upload package.
11. Ask for confirmation before upload or publish.

## Harness Commands

Prefer the repository harness when working inside this project.

Create a pipeline run:

```bash
ai-video-maker run --pipeline pipeline.example.yml --run-id <run_id> --overwrite
```

Approve the brief after user alignment:

```bash
ai-video-maker approve --run runs/<run_id> --gate brief --summary "<summary>"
```

Continue until the next gate:

```bash
ai-video-maker run --run runs/<run_id>
```

Approve the plan before production:

```bash
ai-video-maker approve --run runs/<run_id> --gate plan --summary "<summary>"
```

Inspect state and artifact count:

```bash
ai-video-maker status --run runs/<run_id>
```

Validate a pipeline before creating a run:

```bash
ai-video-maker validate --pipeline pipeline.example.yml
```

Inspect GUI capability dry-run:

```bash
ai-video-maker capabilities --pipeline pipeline.example.yml
```

Inspect local browser demo preflight:

```bash
ai-video-maker capabilities --pipeline templates/pipelines/browser_local_demo.yml
```

P1 pipeline behavior:

```text
pipeline.yml -> brief.yml -> wait for brief approval
brief approved -> storyboard / asset_plan / capability_plan / narration -> wait for plan approval
plan approved -> voice / subtitles / render / QA / package
GUI capability required -> wait for execution approval
upload / publish -> never automatic
```

## Capability Policy

GUI tools are optional capability adapters, not hard dependencies.

Use CLI/API/scripted rendering first when it can complete the task. Use GUI tools only when the task requires real UI interaction.

| Capability | Use When | Avoid When |
|---|---|---|
| `$browser` | Local web app demos, regular websites, screenshots, browser recording, DOM verification | Existing user login state is required |
| `$chrome` | Existing Chrome login state is required, especially YouTube Studio or authenticated dashboards | Cookies, passwords, local storage, or session inspection would be needed |
| `$computer-use` | Desktop GUI apps, OBS, editors, file pickers, native dialogs | A CLI/API can do the task safely |

## Required Confirmation Gates

Ask for confirmation before:

- Uploading files to a third-party platform.
- Publishing a video.
- Setting a video public/unlisted/private on a platform.
- Using an authenticated Chrome session for account-affecting actions.
- Creating OAuth/API credentials.
- Installing or running newly acquired GUI software.
- Deleting or overwriting nontrivial local/cloud files.
- Submitting forms, comments, messages, or any public account action.

Do not ask for confirmation too early. Prepare the files and metadata first, then ask right before the side-effect action.

## Outputs

A complete run should produce:

```text
runs/<run_id>/
  brief.yml
  approvals.yml
  state.json
  plan/storyboard.yml
  plan/asset_plan.yml
  script/narration.zh.txt
  subtitles/captions.srt
  audio/narration.mp3
  render/final_16x9.mp4
  qa/report.md
  package/video.mp4
  package/title.txt
  package/description.md
  package/tags.txt
```

## Quality Bar

- The first 10 seconds must explain value or show the result.
- Every narration section must map to a visual.
- Commands and UI actions must be verified before recording.
- Subtitles must not cover important UI.
- Final video must contain both audio and video streams.
- QA must include duration, codec, audio stream, and keyframe checks.
