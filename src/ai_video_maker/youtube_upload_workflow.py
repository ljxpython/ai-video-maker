from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .artifacts import record_artifact
from .context import RunContext
from .io import read_yaml, write_json, write_yaml


def generate_youtube_upload(ctx: RunContext, mode: str = "dry-run") -> dict[str, Any]:
    package_dir = _package_dir(ctx)
    _require_package(package_dir)
    approvals = read_yaml(ctx.approvals_path)
    plan = _upload_plan(ctx, package_dir, mode)
    upload_dir = ctx.path("upload")
    upload_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(upload_dir / "youtube_upload_plan.yml", plan)
    (upload_dir / "oauth_setup.md").write_text(_oauth_setup(), encoding="utf-8")

    if mode == "execute-upload":
        handoff = _execute_upload(ctx, approvals)
    elif mode == "execute-publish":
        handoff = _execute_publish(ctx, approvals)
    else:
        handoff = _dry_run(ctx, plan)

    write_yaml(upload_dir / "handoff.youtube-upload.yml", handoff)
    record_artifact(ctx, "youtube_upload_plan", "yaml", upload_dir / "youtube_upload_plan.yml", "youtube-upload")
    record_artifact(ctx, "youtube_upload_oauth_setup", "markdown", upload_dir / "oauth_setup.md", "youtube-upload")
    record_artifact(ctx, "youtube_upload_handoff", "yaml", upload_dir / "handoff.youtube-upload.yml", "youtube-upload")
    ctx.update_state(str(handoff["status"]), "youtube-upload", next_action=str(handoff["message"]))
    return handoff


def _dry_run(ctx: RunContext, plan: dict[str, Any]) -> dict[str, Any]:
    result = {
        "status": "passed",
        "dry_run": True,
        "network_requests_performed": False,
        "plan": plan,
    }
    write_json(ctx.path("upload/youtube_dry_run.json"), result)
    ctx.path("upload/youtube_dry_run.md").write_text(_dry_run_markdown(plan), encoding="utf-8")
    record_artifact(ctx, "youtube_dry_run_json", "json", ctx.path("upload/youtube_dry_run.json"), "youtube-upload")
    record_artifact(ctx, "youtube_dry_run_md", "markdown", ctx.path("upload/youtube_dry_run.md"), "youtube-upload")
    return _handoff(ctx, "waiting_for_gate", "upload", "YouTube 上传计划已生成。确认 upload gate 后才能上传 private 视频。", dry_run=True)


def _execute_upload(ctx: RunContext, approvals: dict[str, Any]) -> dict[str, Any]:
    if approvals.get("upload", {}).get("status") != "approved":
        raise PermissionError("upload gate must be approved before YouTube upload")
    if not os.environ.get("AI_VIDEO_MAKER_YOUTUBE_OAUTH"):
        return _handoff(ctx, "blocked", "upload", "缺少 YouTube OAuth 配置，真实上传被阻断。", dry_run=False)
    result = {"status": "blocked", "reason": "real YouTube upload adapter is not implemented in v1", "visibility": "private"}
    write_yaml(ctx.path("upload/youtube_upload_result.yml"), result)
    return _handoff(ctx, "blocked", "upload", "真实上传 adapter 尚未启用。", dry_run=False)


def _execute_publish(ctx: RunContext, approvals: dict[str, Any]) -> dict[str, Any]:
    if approvals.get("publish", {}).get("status") != "approved":
        raise PermissionError("publish gate must be approved before YouTube publish")
    if not ctx.path("upload/youtube_upload_result.yml").exists():
        raise FileNotFoundError("upload/youtube_upload_result.yml is required before publish")
    result = {"status": "blocked", "reason": "real YouTube publish adapter is not implemented in v1"}
    write_yaml(ctx.path("upload/youtube_publish_result.yml"), result)
    return _handoff(ctx, "blocked", "publish", "真实发布 adapter 尚未启用。", dry_run=False)


def _upload_plan(ctx: RunContext, package_dir: Path, mode: str) -> dict[str, Any]:
    return {
        "version": 1,
        "platform": "youtube",
        "mode": mode,
        "requires_gate": "upload",
        "source_package": package_dir.relative_to(ctx.run_dir).as_posix(),
        "video": (package_dir / "video.mp4").relative_to(ctx.run_dir).as_posix(),
        "thumbnail": (package_dir / "thumbnail.png").relative_to(ctx.run_dir).as_posix() if (package_dir / "thumbnail.png").exists() else "",
        "metadata": {
            "title": (package_dir / "title.txt").relative_to(ctx.run_dir).as_posix(),
            "description": (package_dir / "description.md").relative_to(ctx.run_dir).as_posix(),
            "tags": (package_dir / "tags.txt").relative_to(ctx.run_dir).as_posix(),
        },
        "visibility": {
            "upload_default": "private",
            "requested_publish_visibility": "unlisted",
        },
        "safety": {
            "metadata_qa_required": True,
            "upload_gate_required": True,
            "publish_gate_required": True,
            "dry_run_network_requests": False,
        },
    }


def _package_dir(ctx: RunContext) -> Path:
    youtube = ctx.path("package/youtube")
    return youtube if youtube.exists() else ctx.path("package")


def _require_package(package_dir: Path) -> None:
    required = ["video.mp4", "title.txt", "description.md", "tags.txt"]
    missing = [name for name in required if not (package_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"YouTube package is incomplete: {', '.join(missing)}")
    metadata_qa = read_yaml(package_dir / "metadata_qa.yml")
    if not metadata_qa:
        raise FileNotFoundError("metadata_qa.yml is required before upload")
    if metadata_qa.get("status") != "passed":
        raise PermissionError("metadata QA must pass before upload")


def _handoff(ctx: RunContext, status: str, next_gate: str, message: str, *, dry_run: bool) -> dict[str, Any]:
    return {
        "skill": "youtube-upload",
        "run_id": ctx.run_id,
        "status": status,
        "outputs": [
            "upload/youtube_upload_plan.yml",
            "upload/youtube_dry_run.md",
            "upload/youtube_dry_run.json",
            "upload/oauth_setup.md",
            "upload/handoff.youtube-upload.yml",
        ],
        "review_checklist": ["Confirm target account", "Confirm title, description, tags, thumbnail, and visibility"],
        "risks": ["Uploading and publishing affect an external YouTube account"],
        "next_gate": next_gate,
        "next_skill_suggestion": "youtube-upload",
        "revision_skill_suggestion": "publish-package",
        "user_action_required": True,
        "message": message,
        "safety": {
            "dry_run": dry_run,
            "network_requests_performed": False,
            "upload_performed": False,
            "publish_performed": False,
        },
    }


def _dry_run_markdown(plan: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# YouTube Upload Dry Run",
            "",
            "- Network requests performed: `false`",
            f"- Video: `{plan['video']}`",
            f"- Thumbnail: `{plan['thumbnail']}`",
            f"- Default upload visibility: `{plan['visibility']['upload_default']}`",
            "- Current stop: `upload` gate",
            "",
        ]
    )


def _oauth_setup() -> str:
    return "\n".join(
        [
            "# YouTube OAuth Setup",
            "",
            "真实上传功能需要用户在仓库外配置 OAuth 凭据。",
            "",
            "- 不要把 client secret、refresh token、cookie 写入仓库。",
            "- 不要把 OAuth token 写入 `runs/`。",
            "- v1 dry-run 不需要 OAuth，也不会发起网络请求。",
            "",
        ]
    )
