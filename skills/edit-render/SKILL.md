---
name: edit-render
description: Use when AI Video Maker needs to compose storyboard cards, optional browser recording footage, narration audio, and subtitles into a horizontal 16:9 video and hand off to QA.
---

# Edit Render

## Purpose

Render the reviewed `voice-subtitle` outputs into a horizontal YouTube video.

First version supports “browser recording + storyboard card” mixed rendering. If no browser recording exists, render the storyboard as card sections.

## Inputs

- `subtitles/handoff.voice-subtitle.yml`
- `audio/narration.mp3`
- `subtitles/captions.srt`
- `plan/storyboard.yml`
- Optional `assets/browser/handoff.browser-capture.yml`
- Optional `assets/browser/demo.webm`

## Workflow

1. Confirm `voice-subtitle` handoff exists.
2. Render storyboard card sections.
3. Insert browser recording footage when available.
4. Burn captions visually into the frame.
5. Write `render/draft.mp4` and `render/final_16x9.mp4`.
6. Write `render/handoff.edit-render.yml`.
7. Present soft review and recommend `qa-revision`.

## Outputs

```text
runs/<run_id>/render/draft.mp4
runs/<run_id>/render/final_16x9.mp4
runs/<run_id>/render/handoff.edit-render.yml
```

## Handoff

```yaml
skill: edit-render
status: ready_for_review
next_skill_suggestion: qa-revision
revision_skill_suggestion: edit-render
user_action_required: false
```
