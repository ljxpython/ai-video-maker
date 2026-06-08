---
name: browser-capture
description: Use when AI Video Maker needs to operate a local or public webpage after execution approval, capture a screenshot, record a short browser demo, and hand footage to later video workflows.
---

# Browser Capture

## Purpose

Open a local or public webpage, optionally execute `script/screen_actions.yml`, capture screenshots, record a short browser video, and hand the footage to `edit-render`.

This workflow requires the `execution` gate. First version uses Playwright Chromium. It does not use logged-in Chrome state, YouTube Studio, or account-side browser actions.

## Inputs

- `plan/browser_preflight.yml`
- Optional `script/screen_actions.yml`
- Approved `execution` gate

## Workflow

1. Confirm `execution` gate is approved.
2. Read `plan/browser_preflight.yml`.
3. If `script/screen_actions.yml` exists, validate and execute the action DSL.
4. Otherwise open `target_url` from `plan/browser_preflight.yml`.
5. Capture final screenshot, step screenshots, and `assets/browser/demo.webm`.
6. Write QA JSON/Markdown and handoff.
7. Recommend `voice-subtitle`.

## Setup

Install the browser runtime once:

```bash
python -m playwright install chromium
```

## Outputs

```text
runs/<run_id>/assets/browser/demo.webm
runs/<run_id>/assets/browser/screenshot.png
runs/<run_id>/assets/browser/steps/*.png
runs/<run_id>/qa/browser_capture.md
runs/<run_id>/qa/browser_capture.json
runs/<run_id>/qa/browser_actions.json
runs/<run_id>/assets/browser/handoff.browser-capture.yml
```

## Handoff

```yaml
skill: browser-capture
status: ready_for_review
next_skill_suggestion: voice-subtitle
revision_skill_suggestion: browser-capture
user_action_required: false
```
