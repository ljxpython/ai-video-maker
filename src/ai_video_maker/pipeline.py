from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifacts import record_artifact
from .capabilities import GUI_CAPABILITIES, capability_plan_from_pipeline, required_capability_names
from .context import RunContext
from .io import read_yaml, write_yaml
from .stages import generate_voice, package, qa, render


def load_pipeline(path: Path) -> dict[str, Any]:
    data = read_yaml(path)
    if not data:
        raise ValueError(f"pipeline is empty: {path}")
    errors = validate_pipeline(data)
    required_errors = [item for item in errors if item.endswith("is required")]
    if required_errors:
        raise ValueError(required_errors[0])
    return data


def validate_pipeline(pipeline: dict[str, Any]) -> list[str]:
    errors = []
    _require_mapping(errors, pipeline, "project")
    _require_mapping(errors, pipeline, "source")
    _require_mapping(errors, pipeline, "video")

    project = pipeline.get("project", {})
    source = pipeline.get("source", {})
    video = pipeline.get("video", {})
    voice = pipeline.get("voice", {})
    render_config = pipeline.get("render", {})
    upload = pipeline.get("upload", {})

    if isinstance(project, dict):
        _require_text(errors, project, "project.name")
        _require_text(errors, project, "project.type")
    if isinstance(source, dict):
        _require_text(errors, source, "source.type")
        _require_text(errors, source, "source.value")
    if isinstance(video, dict):
        _require_text(errors, video, "video.platform")
        _require_text(errors, video, "video.aspect_ratio")
        _require_text(errors, video, "video.resolution")
        _require_positive_int(errors, video, "video.target_duration")
        _require_text(errors, video, "video.language")

    if "voice" in pipeline:
        if not isinstance(voice, dict):
            errors.append("voice must be a mapping")
        else:
            _require_text(errors, voice, "voice.provider")
            _require_text(errors, voice, "voice.voice")

    if "render" in pipeline:
        if not isinstance(render_config, dict):
            errors.append("render must be a mapping")
        else:
            _require_positive_int(errors, render_config, "render.fps")
            _require_bool(errors, render_config, "render.burn_subtitles")
            _require_bool(errors, render_config, "render.auto_edit")

    if "upload" in pipeline:
        if not isinstance(upload, dict):
            errors.append("upload must be a mapping")
        else:
            _require_bool(errors, upload, "upload.enabled")
            if upload.get("enabled") is True and upload.get("confirmation") != "required":
                errors.append("upload.confirmation must be required when upload.enabled is true")

    capabilities = pipeline.get("capabilities", {})
    if capabilities and not isinstance(capabilities, dict):
        errors.append("capabilities must be a mapping")
    elif isinstance(capabilities, dict):
        for name in GUI_CAPABILITIES:
            config = capabilities.get(name)
            if config is None:
                continue
            if not isinstance(config, dict):
                errors.append(f"capabilities.{name} must be a mapping")
                continue
            _require_bool(errors, config, f"capabilities.{name}.required")

    return errors


def approval_status(ctx: RunContext, gate: str) -> str:
    approvals = read_yaml(ctx.approvals_path)
    gate_data = approvals.get(gate, {})
    return str(gate_data.get("status", "pending"))


def is_gate_approved(ctx: RunContext, gate: str) -> bool:
    return approval_status(ctx, gate) == "approved"


def pipeline_requires_gui(pipeline: dict[str, Any]) -> list[str]:
    return required_capability_names(pipeline)


def initialize_pipeline_run(ctx: RunContext, pipeline_path: Path) -> None:
    pipeline = load_pipeline(pipeline_path)
    write_yaml(ctx.path("pipeline.yml"), pipeline)
    _write_brief(ctx, pipeline)
    ctx.update_state(
        "awaiting_brief_approval",
        "brief",
        pipeline="pipeline.yml",
        next_action=f"approve brief: ai-video-maker approve --run runs/{ctx.run_id} --gate brief",
    )
    record_artifact(ctx, "pipeline", "yaml", ctx.path("pipeline.yml"), "brief")
    record_artifact(ctx, "brief", "yaml", ctx.path("brief.yml"), "brief")


def create_plan_from_pipeline(ctx: RunContext) -> None:
    pipeline = load_pipeline(ctx.path("pipeline.yml"))
    project = pipeline.get("project", {})
    video = pipeline.get("video", {})
    template = str(project.get("type", "general_demo"))

    storyboard = read_yaml(ctx.project_root / "templates" / "storyboards" / f"{template}.yml")
    storyboard["title"] = _project_title(pipeline)
    storyboard["target_duration"] = int(video.get("target_duration", storyboard.get("target_duration", 180)))
    storyboard["aspect_ratio"] = str(video.get("aspect_ratio", storyboard.get("aspect_ratio", "16:9")))

    write_yaml(ctx.path("plan/storyboard.yml"), storyboard)
    write_yaml(ctx.path("plan/asset_plan.yml"), _asset_plan_from_pipeline(pipeline))
    write_yaml(ctx.path("plan/capability_plan.yml"), capability_plan_from_pipeline(pipeline))
    ctx.path("script/narration.zh.txt").write_text(_narration_from_pipeline(pipeline), encoding="utf-8")
    ctx.update_state(
        "awaiting_plan_approval",
        "plan",
        next_action=f"approve plan: ai-video-maker approve --run runs/{ctx.run_id} --gate plan",
    )

    record_artifact(ctx, "storyboard", "yaml", ctx.path("plan/storyboard.yml"), "plan")
    record_artifact(ctx, "asset_plan", "yaml", ctx.path("plan/asset_plan.yml"), "plan")
    record_artifact(ctx, "capability_plan", "yaml", ctx.path("plan/capability_plan.yml"), "plan")
    record_artifact(ctx, "narration_script", "text", ctx.path("script/narration.zh.txt"), "plan")


def advance_pipeline(ctx: RunContext) -> dict[str, str]:
    if not ctx.path("pipeline.yml").exists():
        raise FileNotFoundError(f"pipeline.yml not found in run: {ctx.run_dir}")

    pipeline = load_pipeline(ctx.path("pipeline.yml"))
    if not is_gate_approved(ctx, "brief"):
        ctx.update_state(
            "awaiting_brief_approval",
            "brief",
            next_action=f"approve brief: ai-video-maker approve --run runs/{ctx.run_id} --gate brief",
        )
        return _result(ctx, "waiting for brief approval")

    if not ctx.path("plan/storyboard.yml").exists() or not ctx.path("script/narration.zh.txt").exists():
        create_plan_from_pipeline(ctx)

    if not is_gate_approved(ctx, "plan"):
        ctx.update_state(
            "awaiting_plan_approval",
            "plan",
            next_action=f"approve plan: ai-video-maker approve --run runs/{ctx.run_id} --gate plan",
        )
        return _result(ctx, "waiting for plan approval")

    required_gui = pipeline_requires_gui(pipeline)
    if required_gui and not is_gate_approved(ctx, "execution"):
        ctx.update_state(
            "awaiting_execution_approval",
            "execution",
            required_capabilities=required_gui,
            next_action=f"approve execution: ai-video-maker approve --run runs/{ctx.run_id} --gate execution",
        )
        return _result(ctx, "waiting for execution approval")

    if not ctx.path("audio/narration.mp3").exists():
        generate_voice(ctx)
    if not ctx.path("render/final_16x9.mp4").exists():
        render(ctx)
    if not ctx.path("qa/report.md").exists():
        qa(ctx)
    if not ctx.path("package/video.mp4").exists():
        package(ctx)

    ctx.update_state("package_ready", "package", next_action="")
    return _result(ctx, "pipeline package ready")


def status_summary(ctx: RunContext) -> dict[str, Any]:
    approvals = read_yaml(ctx.approvals_path)
    artifacts = read_yaml(ctx.artifacts_path)
    return {
        "run_id": ctx.run_id,
        "run": f"runs/{ctx.run_id}",
        "state": ctx.state(),
        "approvals": {gate: data.get("status", "pending") for gate, data in approvals.items()},
        "artifact_count": len(artifacts.get("artifacts", [])),
        "artifacts": artifacts.get("artifacts", []),
    }


def _write_brief(ctx: RunContext, pipeline: dict[str, Any]) -> None:
    project = pipeline.get("project", {})
    source = pipeline.get("source", {})
    video = pipeline.get("video", {})
    template = str(project.get("type", "general_demo"))
    brief = read_yaml(ctx.project_root / "templates" / "briefs" / f"{template}.yml")

    brief.update(
        {
            "goal": str(source.get("value", _project_title(pipeline))),
            "audience": str(pipeline.get("audience", "需要理解该视频主题的用户")),
            "platform": str(video.get("platform", brief.get("platform", "youtube"))),
            "duration": int(video.get("target_duration", brief.get("duration", 180))),
            "language": str(video.get("language", brief.get("language", "zh-CN"))),
            "style": str(video.get("style", brief.get("style", "技术讲解，AI 配音，字幕清晰"))),
            "source_material": [source],
            "must_show": pipeline.get("must_show", []),
            "must_avoid": pipeline.get("must_avoid", []),
            "assumptions": pipeline.get("assumptions", []),
            "capabilities": pipeline.get("capabilities", {}),
            "upload": pipeline.get("upload", brief.get("upload", {"enabled": False})),
        }
    )
    write_yaml(ctx.path("brief.yml"), brief)


def _asset_plan_from_pipeline(pipeline: dict[str, Any]) -> dict[str, Any]:
    return {
        "assets": [
            {"id": "narration", "type": "text", "path": "script/narration.zh.txt"},
            {"id": "voice", "type": "audio", "path": "audio/narration.mp3"},
            {"id": "captions", "type": "subtitle", "path": "subtitles/captions.srt"},
        ],
        "capabilities": pipeline.get("capabilities", {}),
    }


def _narration_from_pipeline(pipeline: dict[str, Any]) -> str:
    script = pipeline.get("script", {})
    if isinstance(script, dict) and script.get("narration"):
        return str(script["narration"]).strip() + "\n"

    title = _project_title(pipeline)
    source = pipeline.get("source", {})
    goal = str(source.get("value", title))
    return "\n".join(
        [
            f"这是 {title} 的自动化视频制作任务。",
            f"本次需求是：{goal}",
            "AI Video Maker 会先把需求整理成 brief，再生成 storyboard、素材计划和旁白稿。",
            "在用户确认方案后，它会继续生成 AI 配音、字幕、横屏视频、质检报告和发布包。",
            "当前版本先聚焦横屏 YouTube 说明类视频，浏览器、Chrome 和桌面 GUI 操作会作为后续能力适配器接入。",
            "",
        ]
    )


def _project_title(pipeline: dict[str, Any]) -> str:
    project = pipeline.get("project", {})
    return str(project.get("name", "AI Video Maker"))


def _result(ctx: RunContext, message: str) -> dict[str, str]:
    state = ctx.state()
    return {
        "run": f"runs/{ctx.run_id}",
        "status": str(state.get("status", "")),
        "current_stage": str(state.get("current_stage", "")),
        "message": message,
        "next_action": str(state.get("next_action", "")),
    }


def _require_mapping(errors: list[str], data: dict[str, Any], key: str) -> None:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} is required")


def _require_text(errors: list[str], data: dict[str, Any], dotted_key: str) -> None:
    key = dotted_key.split(".")[-1]
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{dotted_key} must be a non-empty string")


def _require_positive_int(errors: list[str], data: dict[str, Any], dotted_key: str) -> None:
    key = dotted_key.split(".")[-1]
    value = data.get(key)
    if not isinstance(value, int) or value <= 0:
        errors.append(f"{dotted_key} must be a positive integer")


def _require_bool(errors: list[str], data: dict[str, Any], dotted_key: str) -> None:
    key = dotted_key.split(".")[-1]
    value = data.get(key)
    if not isinstance(value, bool):
        errors.append(f"{dotted_key} must be true or false")
