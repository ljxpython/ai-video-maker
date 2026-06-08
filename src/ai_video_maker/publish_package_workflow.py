from __future__ import annotations

import shutil
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .artifacts import record_artifact
from .context import RunContext
from .io import read_yaml, write_yaml
from .renderer import DEFAULT_FONT
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
    youtube_dir = package_dir / "youtube"
    package_dir.mkdir(parents=True, exist_ok=True)
    youtube_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(final_video, package_video)
    shutil.copyfile(final_video, youtube_dir / "video.mp4")

    pipeline = pipeline_config(ctx)
    metadata = _metadata(pipeline)
    chapters = _chapters(ctx)
    title_options = _title_options(metadata)
    for target_dir in [package_dir, youtube_dir]:
        (target_dir / "title.txt").write_text(metadata["title"] + "\n", encoding="utf-8")
        (target_dir / "title_options.md").write_text(title_options, encoding="utf-8")
        (target_dir / "description.md").write_text(metadata["description"] + "\n## Chapters\n\n" + chapters + "\n", encoding="utf-8")
        (target_dir / "chapters.txt").write_text(chapters, encoding="utf-8")
        (target_dir / "tags.txt").write_text(",".join(metadata["tags"]) + "\n", encoding="utf-8")
        (target_dir / "upload_checklist.md").write_text(_upload_checklist(ctx), encoding="utf-8")
        _write_thumbnail(ctx, target_dir / "thumbnail.png", metadata)
        write_yaml(target_dir / "metadata_qa.yml", _metadata_qa(ctx, target_dir))

    shorts_video = ctx.path("render/final_9x16.mp4")
    if shorts_video.exists():
        shorts_dir = package_dir / "shorts"
        shorts_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(shorts_video, shorts_dir / "video.mp4")
        (shorts_dir / "title.txt").write_text(metadata["title"][:95] + "\n", encoding="utf-8")
        (shorts_dir / "description.md").write_text(metadata["description"], encoding="utf-8")
        (shorts_dir / "tags.txt").write_text(",".join(metadata["tags"]) + "\n", encoding="utf-8")

    handoff = _handoff(ctx)
    write_yaml(package_dir / "handoff.publish-package.yml", handoff)

    record_artifact(ctx, "package_video", "video", package_video, "publish-package")
    record_artifact(ctx, "package_title", "text", package_dir / "title.txt", "publish-package")
    record_artifact(ctx, "package_thumbnail", "image", package_dir / "thumbnail.png", "publish-package")
    record_artifact(ctx, "package_chapters", "text", package_dir / "chapters.txt", "publish-package")
    record_artifact(ctx, "package_title_options", "markdown", package_dir / "title_options.md", "publish-package")
    record_artifact(ctx, "package_metadata_qa", "yaml", package_dir / "metadata_qa.yml", "publish-package")
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


def _title_options(metadata: dict[str, Any]) -> str:
    title = str(metadata["title"])
    options = [
        title,
        f"{title}：AI 视频制作工作流实操",
        f"用 AI 自动生成技术视频：{title}",
        f"{title} 项目介绍与演示",
    ]
    return "# Title Options\n\n" + "\n".join(f"{index}. {item[:95]}" for index, item in enumerate(options, start=1)) + "\n"


def _chapters(ctx: RunContext) -> str:
    storyboard = read_yaml(ctx.path("plan/storyboard.yml"))
    sections = storyboard.get("sections", []) if isinstance(storyboard, dict) else []
    if not isinstance(sections, list) or not sections:
        return "00:00 开场与目标\n00:15 工作流概览\n00:35 实操演示\n01:00 结果与下一步\n"
    elapsed = 0
    lines = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        title = str(section.get("purpose") or section.get("id") or "章节")
        lines.append(f"{elapsed // 60:02}:{elapsed % 60:02} {title}")
        duration = section.get("duration", 10)
        elapsed += duration if isinstance(duration, int) and duration > 0 else 10
    return "\n".join(lines).rstrip() + "\n"


def _write_thumbnail(ctx: RunContext, output: Any, metadata: dict[str, Any]) -> None:
    output_path = output
    source = ctx.path("qa/screenshots/frame_6s.png")
    if source.exists():
        try:
            with Image.open(source) as source_image:
                image = source_image.convert("RGB").resize((1280, 720))
        except Exception:
            image = Image.new("RGB", (1280, 720), (18, 26, 36))
    else:
        image = Image.new("RGB", (1280, 720), (18, 26, 36))
    overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 95))
    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.truetype(str(DEFAULT_FONT), 72)
    small_font = ImageFont.truetype(str(DEFAULT_FONT), 34)
    draw.text((72, 110), str(metadata["title"])[:32], font=title_font, fill=(255, 255, 255))
    draw.text((76, 225), "AI Video Maker", font=small_font, fill=(255, 209, 102))
    draw.rounded_rectangle((72, 590, 430, 650), radius=12, fill=(255, 209, 102, 230))
    draw.text((98, 604), "YouTube Ready", font=small_font, fill=(18, 26, 36))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path)


def _metadata_qa(ctx: RunContext, package_dir: Any) -> dict[str, Any]:
    thumbnail_path = package_dir / "thumbnail.png"
    title_text = (package_dir / "title.txt").read_text(encoding="utf-8").strip()
    description_text = (package_dir / "description.md").read_text(encoding="utf-8").strip()
    chapters_text = (package_dir / "chapters.txt").read_text(encoding="utf-8").strip()
    tags_text = (package_dir / "tags.txt").read_text(encoding="utf-8").strip()
    thumbnail_ok = False
    if thumbnail_path.exists():
        try:
            with Image.open(thumbnail_path) as thumbnail_image:
                thumbnail_ok = thumbnail_image.size == (1280, 720)
        except Exception:
            thumbnail_ok = False
    checks = {
        "video_exists": (package_dir / "video.mp4").exists(),
        "thumbnail_exists": thumbnail_path.exists(),
        "thumbnail_size_1280x720": thumbnail_ok,
        "title_exists": bool(title_text),
        "title_length_ok": 0 < len(title_text) <= 95,
        "description_exists": bool(description_text),
        "chapters_start_at_zero": chapters_text.startswith("00:00"),
        "tags_exists": bool(tags_text),
        "tags_count_ok": 3 <= len([item for item in tags_text.split(",") if item.strip()]) <= 15,
    }
    approvals = read_yaml(ctx.approvals_path)
    checks["upload_gate_pending"] = approvals.get("upload", {}).get("status", "pending") == "pending"
    checks["publish_gate_pending"] = approvals.get("publish", {}).get("status", "pending") == "pending"
    return {"status": "passed" if all(checks.values()) else "failed", "checks": checks}


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
            "- [ ] Review `package/thumbnail.png`",
            "- [ ] Review `package/title.txt`",
            "- [ ] Review `package/title_options.md`",
            "- [ ] Review `package/description.md`",
            "- [ ] Review `package/chapters.txt`",
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
            "package/thumbnail.png",
            "package/title.txt",
            "package/title_options.md",
            "package/description.md",
            "package/chapters.txt",
            "package/tags.txt",
            "package/metadata_qa.yml",
            "package/upload_checklist.md",
            "package/youtube/video.mp4",
            "package/youtube/thumbnail.png",
            "package/youtube/title.txt",
            "package/youtube/title_options.md",
            "package/youtube/description.md",
            "package/youtube/chapters.txt",
            "package/youtube/tags.txt",
            "package/youtube/metadata_qa.yml",
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
