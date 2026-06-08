from __future__ import annotations

import shutil
from typing import Any

from .artifacts import record_artifact
from .context import RunContext
from .io import read_yaml, write_yaml
from .stages import pipeline_config


def generate_publish_package(ctx: RunContext) -> dict[str, Any]:
    qa_handoff = read_yaml(ctx.path("qa/handoff.qa-revision.yml"))
    if qa_handoff.get("skill") != "qa-revision":
        raise FileNotFoundError("qa/handoff.qa-revision.yml is required before publish-package")
    if qa_handoff.get("status") not in {"ready_for_review", "done"}:
        raise PermissionError("qa-revision must pass before publish-package")

    final_video = ctx.path("render/final_16x9.mp4")
    if not final_video.exists():
        raise FileNotFoundError("render/final_16x9.mp4 is required before publish-package")

    package_dir = ctx.path("package")
    package_video = package_dir / "video.mp4"
    package_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(final_video, package_video)

    pipeline = pipeline_config(ctx)
    metadata = _metadata(pipeline)
    (package_dir / "title.txt").write_text(metadata["title"] + "\n", encoding="utf-8")
    (package_dir / "description.md").write_text(metadata["description"], encoding="utf-8")
    (package_dir / "tags.txt").write_text(",".join(metadata["tags"]) + "\n", encoding="utf-8")
    (package_dir / "upload_checklist.md").write_text(_upload_checklist(ctx), encoding="utf-8")

    handoff = _handoff(ctx)
    write_yaml(package_dir / "handoff.publish-package.yml", handoff)

    record_artifact(ctx, "package_video", "video", package_video, "publish-package")
    record_artifact(ctx, "package_title", "text", package_dir / "title.txt", "publish-package")
    record_artifact(ctx, "package_description", "markdown", package_dir / "description.md", "publish-package")
    record_artifact(ctx, "package_tags", "text", package_dir / "tags.txt", "publish-package")
    record_artifact(ctx, "upload_checklist", "markdown", package_dir / "upload_checklist.md", "publish-package")
    record_artifact(ctx, "publish_package_handoff", "yaml", package_dir / "handoff.publish-package.yml", "publish-package")

    ctx.update_state("publish_package_ready", "publish-package", next_action="review package; next gate: upload")
    return handoff


def _metadata(pipeline: dict[str, Any]) -> dict[str, Any]:
    project = pipeline.get("project", {}) if isinstance(pipeline.get("project"), dict) else {}
    source = pipeline.get("source", {}) if isinstance(pipeline.get("source"), dict) else {}
    video = pipeline.get("video", {}) if isinstance(pipeline.get("video"), dict) else {}
    title = str(project.get("name") or "AI Video Maker").strip()
    style = str(video.get("style") or "AI-assisted video workflow").strip()
    source_value = str(source.get("value") or "视频需求").strip()
    description = "\n".join(
        [
            f"# {title}",
            "",
            "本视频由 AI Video Maker 的 skills-first 工作流生成。",
            "",
            f"- 视频需求：{source_value}",
            f"- 视频风格：{style}",
            "- 制作链路：brief -> plan -> script -> voice-subtitle -> edit-render -> qa-revision -> publish-package",
            "",
            "上传和发布需要用户在 `upload` 与 `publish` gate 明确确认后再执行。",
            "",
        ]
    )
    return {
        "title": title[:95],
        "description": description,
        "tags": ["AI video", "technical demo", "automation", "Python", "YouTube"],
    }


def _upload_checklist(ctx: RunContext) -> str:
    approvals = read_yaml(ctx.approvals_path)
    upload_status = approvals.get("upload", {}).get("status", "pending")
    publish_status = approvals.get("publish", {}).get("status", "pending")
    return "\n".join(
        [
            "# Upload Checklist",
            "",
            f"- [ ] Confirm target account (`upload` gate: `{upload_status}`)",
            "- [ ] Review `package/video.mp4`",
            "- [ ] Review `package/title.txt`",
            "- [ ] Review `package/description.md`",
            "- [ ] Review `package/tags.txt`",
            f"- [ ] Confirm visibility and timing (`publish` gate: `{publish_status}`)",
            "",
            "No upload or publish action has been executed by this package step.",
            "",
        ]
    )


def _handoff(ctx: RunContext) -> dict[str, Any]:
    return {
        "skill": "publish-package",
        "run_id": ctx.run_id,
        "status": "ready_for_gate",
        "outputs": [
            "package/video.mp4",
            "package/title.txt",
            "package/description.md",
            "package/tags.txt",
            "package/upload_checklist.md",
            "package/handoff.publish-package.yml",
        ],
        "review_checklist": [
            "Confirm package video is the intended final render",
            "Confirm title, description, and tags are accurate",
            "Confirm target YouTube account and visibility before upload",
        ],
        "risks": ["Uploading or publishing affects an external account and requires explicit approval"],
        "next_gate": "upload",
        "next_skill_suggestion": None,
        "revision_skill_suggestion": "publish-package",
        "user_action_required": True,
        "user_message": "Please review the publishing package. If you want platform upload, approve the upload gate first.",
    }
