---
name: edit-render
description: Use when AI Video Maker needs to compose storyboard cards, optional browser recordings, terminal cards, narration audio, and subtitles into horizontal or vertical videos and hand off to QA.
---

# Edit Render

## Purpose

Render the reviewed `voice-subtitle` outputs into YouTube 16:9 and optional Shorts 9:16 videos.

Current version supports storyboard cards, browser recording footage, and terminal cards.

## Inputs

- `subtitles/handoff.voice-subtitle.yml`
- `audio/narration.mp3`
- `subtitles/captions.srt`
- `plan/storyboard.yml`
- Optional `assets/browser/handoff.browser-capture.yml`
- Optional `assets/browser/demo.webm`
- Optional `assets/terminal/handoff.terminal-capture.yml`
- Optional render profile: `youtube_16x9` or `shorts_9x16`

## Workflow

1. Confirm `voice-subtitle` handoff exists.
2. Render storyboard card sections.
3. Insert browser recording or terminal cards when available.
4. Burn captions visually into the frame.
5. Write profile outputs such as `render/final_16x9.mp4` and `render/final_9x16.mp4`.
6. Write `render/handoff.edit-render.yml`.
7. Present soft review and recommend `qa-revision`.

## Outputs

```text
runs/<run_id>/render/draft.mp4
runs/<run_id>/render/final_16x9.mp4
runs/<run_id>/render/final_9x16.mp4
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
