---
name: video-brief
description: Use when AI Video Maker needs to turn a raw user video request into a structured brief for technical, product, tutorial, SOP, repository, API, bug reproduction, or release note videos. Produces the brief review package and stops at the brief gate.
---

# Video Brief

## Purpose

Turn a raw video request into a structured production brief. This skill is the first child workflow after `ai-video-maker` / `ai-video-orchestrator`.

Do not plan shots, record screens, generate voice, edit video, upload, or publish. Those belong to later skills.

## Inputs

- User request.
- Target platform if provided.
- Audience if provided.
- Duration, language, style, constraints, and source material if provided.
- Existing run directory if the orchestrator has already created one.

## Workflow

1. Extract the user's goal, audience, platform, format, duration, language, style, source material, constraints, and success criteria.
2. If information is missing but a safe assumption is obvious, state the assumption.
3. Ask at most three focused questions only when missing information changes the production plan.
4. Produce a concise `brief.yml` payload or update `runs/<run_id>/brief.yml` when the harness is available.
5. Stop at the `brief` gate and ask the user to review.
6. Tell the user that the next recommended skill is `video-plan` after approval.

## Brief Fields

Use this shape when writing or presenting the brief:

```yaml
project:
  name: ""
  video_type: ""
goal:
  primary: ""
  success_criteria: []
audience:
  target: ""
  prior_knowledge: ""
platform:
  name: "youtube"
  aspect_ratio: "16:9"
  target_duration_seconds: 60
style:
  language: "zh-CN"
  tone: ""
  voice: ""
source:
  type: ""
  location: ""
constraints: []
unknowns: []
```

## Review Checklist

Ask the user to review:

- Goal and success criteria.
- Audience and assumed prior knowledge.
- Platform, aspect ratio, and target duration.
- Language, tone, and voice style.
- Source material and constraints.
- Open questions or assumptions.

## Handoff

End with a handoff block:

```yaml
skill: video-brief
run_id: demo
status: ready_for_gate
outputs:
  - brief.yml
review_checklist:
  - Confirm goal, audience, platform, duration, style, and constraints
risks: []
next_gate: brief
next_skill_suggestion: video-plan
revision_skill_suggestion: video-brief
user_action_required: true
user_message: "Please review the brief. If approved, the next recommended skill is video-plan."
```
