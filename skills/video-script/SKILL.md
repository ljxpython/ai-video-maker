---
name: video-script
description: Use when AI Video Maker needs to turn an approved video plan into narration, subtitle draft, screen action script, and shot notes before capture, voice, subtitle, and render workflows.
---

# Video Script

## Purpose

Turn the approved plan into production-ready narration and screen action instructions.

This is a soft-review workflow. It does not require a hard gate unless the script changes the approved plan, introduces risky execution, or requires account-side actions.

## Inputs

- Approved `brief.yml`.
- Approved `plan/storyboard.yml`.
- `plan/asset_plan.yml`.
- `plan/capability_plan.yml`.
- User feedback from the `plan` gate.

## Workflow

1. Read the approved brief and storyboard.
2. Write narration that sounds natural when spoken by an AI voice.
3. Keep subtitle lines short and readable.
4. Write screen action instructions for browser, Chrome, terminal, desktop GUI, or generated visuals.
5. Add shot notes for timing, emphasis, callouts, and transitions.
6. Check that every narration segment maps to a visual.
7. Present the script for soft review.
8. Recommend the next skill:
   - `browser-capture` when real browser, Chrome, or GUI capture is needed.
   - `voice-subtitle` when visuals are already available or generated.
   - `video-plan` when the script reveals a plan problem.

## Outputs

When the harness is available, write:

```text
runs/<run_id>/script/narration.zh.txt
runs/<run_id>/script/screen_actions.md
runs/<run_id>/script/subtitle_draft.srt
runs/<run_id>/script/shot_notes.md
```

## Script Quality Bar

- The first 10 seconds explain value or show the result.
- Each section has one clear purpose.
- Sentences are easy for AI voice to pronounce.
- Subtitle lines are short enough for screen reading.
- Screen actions are executable by a later capture workflow.
- No upload, publish, login, or account-side action is introduced without a gate.

## Review Checklist

Ask the user to review:

- Tone and pacing.
- Whether the narration says the right thing.
- Whether screen actions match what should be shown.
- Whether any section is too long, too vague, or off-topic.
- Whether to continue to capture or return to plan/script revision.

## Handoff

End with a handoff block:

```yaml
skill: video-script
run_id: demo
status: ready_for_review
outputs:
  - script/narration.zh.txt
  - script/screen_actions.md
  - script/subtitle_draft.srt
  - script/shot_notes.md
review_checklist:
  - Confirm narration tone, subtitle readability, and screen action order
risks:
  - execution gate is required before browser, Chrome, or desktop capture
next_gate: null
next_skill_suggestion: browser-capture
revision_skill_suggestion: video-script
user_action_required: false
user_message: "Please review the narration and screen actions. If approved, the next recommended skill is browser-capture when capture is needed, otherwise voice-subtitle."
```
