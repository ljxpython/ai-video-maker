---
name: video-plan
description: Use when AI Video Maker needs to convert an approved video brief into a storyboard, asset plan, capability plan, production steps, and plan gate review package.
---

# Video Plan

## Purpose

Convert an approved `brief.yml` into a concrete production plan.

Do not record, generate final narration audio, render final video, upload, or publish. This skill prepares the plan and stops at the `plan` gate.

## Inputs

- Approved `brief.yml`.
- User feedback from the `brief` gate.
- Existing pipeline or run state when available.

## Workflow

1. Read the approved brief.
2. Create a chapter-level storyboard with visual intent, narration intent, and approximate timing.
3. Create an asset plan listing generated graphics, screenshots, browser recordings, terminal captures, existing files, or desktop actions.
4. Create a capability plan for `$browser`, `$chrome`, `$computer-use`, CLI tools, APIs, and scripted rendering.
5. Identify hard gates required by the plan, especially `execution`, `upload`, and `publish`.
6. Produce detailed execution steps that a later skill can follow.
7. Stop at the `plan` gate and ask the user to review.
8. Tell the user that the next recommended skill is usually `video-script`.

## Outputs

When the harness is available, write:

```text
runs/<run_id>/plan/storyboard.yml
runs/<run_id>/plan/asset_plan.yml
runs/<run_id>/plan/capability_plan.yml
```

## Plan Quality Bar

- Each chapter has a clear visual target.
- Each narration section maps to visible action or visual material.
- The first 10 seconds show value or outcome.
- GUI actions are isolated behind `execution` gate.
- Upload and publish are isolated behind their own gates.
- The plan is specific enough for `video-script` and capture skills to execute.

## Review Checklist

Ask the user to review:

- Chapter structure and timing.
- Visual plan and asset sources.
- Capability choices: browser, Chrome, desktop GUI, CLI, API, or scripted rendering.
- Risks and required gates.
- Whether the next step should be `video-script` or plan revision.

## Handoff

End with a handoff block:

```yaml
skill: video-plan
run_id: demo
status: ready_for_gate
outputs:
  - plan/storyboard.yml
  - plan/asset_plan.yml
  - plan/capability_plan.yml
review_checklist:
  - Confirm chapter structure, asset plan, capability plan, and production steps
risks:
  - execution gate may be required for browser, Chrome, or desktop capture
next_gate: plan
next_skill_suggestion: video-script
revision_skill_suggestion: video-plan
user_action_required: true
user_message: "Please review the storyboard, asset plan, and capability plan. If approved, the next recommended skill is video-script."
```
