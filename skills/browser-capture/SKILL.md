---
name: browser-capture
description: Use when AI Video Maker needs to operate a local or public webpage after execution approval, capture a screenshot, record a short browser demo, and hand footage to later video workflows.
---

# Browser Capture

## Purpose

Open a local or public webpage, capture a screenshot, record a short browser video, and hand the footage to `edit-render`.

This workflow requires the `execution` gate. First version uses Playwright Chromium. It does not use logged-in Chrome state, YouTube Studio, or account-side browser actions.

## Inputs

- `plan/browser_preflight.yml`
- Approved `execution` gate

## Workflow

1. Confirm `execution` gate is approved.
2. Read `plan/browser_preflight.yml`.
3. Open `target_url`.
4. Wait for the page to load.
5. Capture `assets/browser/screenshot.png`.
6. Record `assets/browser/demo.webm`.
7. Write `qa/browser_capture.md`.
8. Write `assets/browser/handoff.browser-capture.yml`.
9. Recommend `voice-subtitle`.

## Setup

Install the browser runtime once:

```bash
python -m playwright install chromium
```

## Outputs

```text
runs/<run_id>/assets/browser/demo.webm
runs/<run_id>/assets/browser/screenshot.png
runs/<run_id>/qa/browser_capture.md
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
