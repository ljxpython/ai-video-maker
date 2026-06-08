---
name: youtube-upload
description: Use when AI Video Maker needs to create a YouTube upload plan or dry-run after publish-package, and only upload or publish after explicit upload and publish gates.
---

# YouTube Upload

## Purpose

Read the local publishing package, create a YouTube upload plan, and stop at the correct gate.

Default mode is dry-run. It performs no network requests and does not upload or publish.

## Gate Policy

- `upload` gate is required before uploading a private video.
- `publish` gate is required before changing visibility to unlisted or public.
- OAuth tokens, client secrets, cookies, and browser session data must never be written to the repo or run outputs.

## Outputs

```text
runs/<run_id>/upload/youtube_upload_plan.yml
runs/<run_id>/upload/youtube_dry_run.md
runs/<run_id>/upload/youtube_dry_run.json
runs/<run_id>/upload/oauth_setup.md
runs/<run_id>/upload/handoff.youtube-upload.yml
```
