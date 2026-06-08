---
name: terminal-capture
description: Use when AI Video Maker needs to run approved safe terminal commands, capture stdout/stderr, render terminal output cards, and hand them to edit-render.
---

# Terminal Capture

## Purpose

Run approved safe terminal commands from `script/terminal_actions.yml`, write logs, render terminal cards, and hand them to `edit-render`.

Requires the `execution` gate. Do not run arbitrary user commands, installs, deletes, pushes, system changes, or secret-reading commands.

## Inputs

- `script/terminal_actions.yml`
- Approved `execution` gate

## Workflow

1. Confirm `execution` gate.
2. Validate commands against the allowlist.
3. Run commands without shell expansion.
4. Redact local paths, emails, tokens, cookies, and secrets from output.
5. Write logs, cards, QA report, and handoff.
6. Recommend `edit-render` when successful.

## Outputs

```text
runs/<run_id>/assets/terminal/logs/*.txt
runs/<run_id>/assets/terminal/cards/*.png
runs/<run_id>/qa/terminal_capture.md
runs/<run_id>/qa/terminal_capture.json
runs/<run_id>/assets/terminal/handoff.terminal-capture.yml
```
