---
name: publish-package
description: Use when AI Video Maker needs to prepare a YouTube-ready publishing package after QA, without uploading or publishing anything.
---

# Publish Package

## Purpose

Prepare local publishing files after `qa-revision` passes.

This workflow does not upload, publish, schedule, log in, open YouTube Studio, or touch an external account.

## Inputs

- `qa/handoff.qa-revision.yml`
- `render/final_16x9.mp4`
- Optional `pipeline.yml`

## Workflow

1. Confirm `qa-revision` handoff exists and passed.
2. Copy final video into `package/video.mp4`.
3. Generate title, description, tags, and upload checklist.
4. Write `package/handoff.publish-package.yml`.
5. Stop at the `upload` gate.

## Outputs

```text
runs/<run_id>/package/video.mp4
runs/<run_id>/package/title.txt
runs/<run_id>/package/description.md
runs/<run_id>/package/tags.txt
runs/<run_id>/package/upload_checklist.md
runs/<run_id>/package/handoff.publish-package.yml
```

## Handoff

```yaml
skill: publish-package
status: ready_for_gate
next_gate: upload
next_skill_suggestion: null
revision_skill_suggestion: publish-package
user_action_required: true
```
