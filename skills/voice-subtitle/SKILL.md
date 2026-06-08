---
name: voice-subtitle
description: Use when AI Video Maker needs to turn reviewed video-script outputs into AI narration audio, formal subtitles, review checklist, and handoff to edit-render.
---

# Voice Subtitle

## Purpose

Generate AI narration audio and formal subtitles after `video-script` is ready for review.

This is a soft-review workflow. It does not render the video, edit the timeline, upload, publish, or use browser/Chrome/desktop GUI.

## Inputs

- `script/handoff.video-script.yml`
- `script/narration.zh.txt`
- `script/subtitle_draft.srt`
- `pipeline.yml` voice settings when available.

## Workflow

1. Confirm `script/handoff.video-script.yml` exists and came from `video-script`.
2. Generate narration audio from `script/narration.zh.txt`.
3. Generate formal captions at `subtitles/captions.srt`.
4. Check that audio and captions exist.
5. Write `subtitles/handoff.voice-subtitle.yml`.
6. Present a soft review and recommend `edit-render`.

## Outputs

```text
runs/<run_id>/audio/narration.mp3
runs/<run_id>/subtitles/captions.srt
runs/<run_id>/subtitles/handoff.voice-subtitle.yml
```

## Review Checklist

Ask the user to review:

- Audio file exists and is playable.
- Voice style matches the brief.
- Subtitle timing exists.
- Subtitle text is readable before render.
- Whether to continue to `edit-render` or return to `video-script` / `voice-subtitle` revision.

## Handoff

End with a handoff block:

```yaml
skill: voice-subtitle
run_id: demo
status: ready_for_review
outputs:
  - audio/narration.mp3
  - subtitles/captions.srt
review_checklist:
  - Confirm narration audio exists and is playable
  - Confirm subtitle timing exists
  - Confirm subtitle text is readable before render
risks: []
next_gate: null
next_skill_suggestion: edit-render
revision_skill_suggestion: voice-subtitle
user_action_required: false
user_message: "Please review the generated voice and captions. If approved, the next recommended skill is edit-render."
```
