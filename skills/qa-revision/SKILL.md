---
name: qa-revision
description: Use when AI Video Maker needs to inspect an edit-render output, verify video/audio/subtitles/keyframe evidence, and route either to publish-package or the right revision skill.
---

# QA Revision

## Purpose

Check the rendered video before packaging. This is a soft-review workflow.

## Inputs

- `render/handoff.edit-render.yml`
- `render/final_16x9.mp4`
- `subtitles/captions.srt`

## Workflow

1. Confirm `edit-render` handoff exists and is ready.
2. Check final video file exists.
3. Run ffprobe and verify video and audio streams.
4. Check subtitles are present.
5. Extract a keyframe screenshot.
6. Write QA report and handoff.
7. Recommend `publish-package` when checks pass.
8. Recommend `edit-render` or `voice-subtitle` when checks fail.

## Outputs

```text
runs/<run_id>/qa/report.md
runs/<run_id>/qa/ffprobe.json
runs/<run_id>/qa/screenshots/frame_6s.png
runs/<run_id>/qa/handoff.qa-revision.yml
```

## Handoff

```yaml
skill: qa-revision
status: ready_for_review
next_skill_suggestion: publish-package
revision_skill_suggestion: edit-render
user_action_required: false
```
