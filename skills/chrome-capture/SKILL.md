---
name: chrome-capture
description: Use when AI Video Maker needs to plan or record user-visible Chrome results for logged-in pages after execution approval, without reading cookies, localStorage, passwords, or tokens.
---

# Chrome Capture

## Purpose

Plan and record user-visible Chrome operation results for authenticated webpages.

Requires the `execution` gate before recording results. Upload and publish actions require their own gates and are not executed by this skill.

## Inputs

- Optional `pipeline.yml` Chrome capability config
- Approved `execution` gate before result recording
- Optional user-provided screenshot evidence

## Outputs

```text
runs/<run_id>/plan/chrome_operation.yml
runs/<run_id>/assets/chrome/*.png
runs/<run_id>/qa/chrome_operation.md
runs/<run_id>/qa/chrome_operation.json
runs/<run_id>/assets/chrome/handoff.chrome-capture.yml
```
