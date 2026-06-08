---
name: desktop-capture
description: Use when AI Video Maker needs to plan or record user-visible desktop GUI results through computer-use after execution approval, without unsafe file, upload, publish, or system-setting side effects.
---

# Desktop Capture

## Purpose

Plan and record user-visible desktop GUI operation results for apps, file pickers, native dialogs, OBS, or editors.

Requires the `execution` gate before recording results. Destructive file operations, uploads, publishing, and system settings require explicit additional confirmation.

## Inputs

- Optional `pipeline.yml` computer_use capability config
- Approved `execution` gate before result recording
- Optional user-provided screenshot evidence

## Outputs

```text
runs/<run_id>/plan/desktop_operation.yml
runs/<run_id>/assets/desktop/*.png
runs/<run_id>/qa/desktop_operation.md
runs/<run_id>/qa/desktop_operation.json
runs/<run_id>/assets/desktop/handoff.desktop-capture.yml
```
