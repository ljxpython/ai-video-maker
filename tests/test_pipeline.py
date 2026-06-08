import tempfile
import unittest
from pathlib import Path

import ai_video_maker.pipeline as pipeline_module
from ai_video_maker.context import create_run
from ai_video_maker.io import read_yaml
from ai_video_maker.pipeline import advance_pipeline, initialize_pipeline_run, status_summary, validate_pipeline
from ai_video_maker.stages import approve_gate


class PipelineTests(unittest.TestCase):
    def test_pipeline_initializes_brief_and_waits_for_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_path = write_project_files(root, gui_required=False)
            ctx = create_run(root, run_id="pipeline-run")

            initialize_pipeline_run(ctx, pipeline_path)
            result = advance_pipeline(ctx)

            self.assertEqual(result["status"], "awaiting_brief_approval")
            self.assertTrue(ctx.path("brief.yml").exists())
            self.assertFalse(ctx.path("plan/storyboard.yml").exists())
            self.assertEqual(read_yaml(ctx.path("brief.yml"))["goal"], "介绍 AI Video Maker")

    def test_brief_approval_allows_plan_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_path = write_project_files(root, gui_required=False)
            ctx = create_run(root, run_id="pipeline-run")
            initialize_pipeline_run(ctx, pipeline_path)

            approve_gate(ctx, "brief", summary="brief ok")
            result = advance_pipeline(ctx)

            self.assertEqual(result["status"], "awaiting_plan_approval")
            self.assertTrue(ctx.path("plan/storyboard.yml").exists())
            self.assertTrue(ctx.path("plan/asset_plan.yml").exists())
            self.assertTrue(ctx.path("plan/capability_plan.yml").exists())
            self.assertTrue(ctx.path("script/narration.zh.txt").exists())

            storyboard = read_yaml(ctx.path("plan/storyboard.yml"))
            self.assertEqual(sum(section["duration"] for section in storyboard["sections"]), 60)
            self.assertTrue(all(section["visual"] for section in storyboard["sections"]))
            self.assertTrue(all(section["narration"] for section in storyboard["sections"]))

            artifacts = read_yaml(ctx.artifacts_path)
            ids = {item["id"] for item in artifacts["artifacts"]}
            self.assertIn("pipeline", ids)
            self.assertIn("asset_plan", ids)
            self.assertIn("capability_plan", ids)

    def test_gui_capability_requires_execution_approval_before_production(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_path = write_project_files(root, gui_required=True)
            ctx = create_run(root, run_id="pipeline-run")
            initialize_pipeline_run(ctx, pipeline_path)

            approve_gate(ctx, "brief", summary="brief ok")
            advance_pipeline(ctx)
            approve_gate(ctx, "plan", summary="plan ok")
            result = advance_pipeline(ctx)

            self.assertEqual(result["status"], "awaiting_execution_approval")
            self.assertEqual(ctx.state()["required_capabilities"], ["browser"])
            self.assertFalse(ctx.path("audio/narration.mp3").exists())

    def test_browser_target_generates_preflight_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_path = write_project_files(root, gui_required=True, browser_target_url="http://localhost:8000")
            ctx = create_run(root, run_id="browser-run")
            initialize_pipeline_run(ctx, pipeline_path)

            approve_gate(ctx, "brief", summary="brief ok")
            advance_pipeline(ctx)

            preflight = read_yaml(ctx.path("plan/browser_preflight.yml"))
            self.assertEqual(preflight["target_url"], "http://localhost:8000")
            self.assertEqual(preflight["target_kind"], "local_web")
            self.assertEqual(preflight["status"], "ready_for_execution_gate")

            artifacts = read_yaml(ctx.artifacts_path)
            ids = {item["id"] for item in artifacts["artifacts"]}
            self.assertIn("browser_preflight", ids)

    def test_status_summary_includes_approvals_and_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_path = write_project_files(root, gui_required=False)
            ctx = create_run(root, run_id="pipeline-run")
            initialize_pipeline_run(ctx, pipeline_path)

            summary = status_summary(ctx)

            self.assertEqual(summary["run"], "runs/pipeline-run")
            self.assertEqual(summary["approvals"]["brief"], "pending")
            self.assertEqual(summary["artifact_count"], 2)

    def test_validate_pipeline_accepts_valid_config(self):
        pipeline = {
            "project": {"name": "AI Video Maker", "type": "general_demo"},
            "source": {"type": "user_request", "value": "介绍项目"},
            "video": {
                "platform": "youtube",
                "aspect_ratio": "16:9",
                "resolution": "1920x1080",
                "target_duration": 60,
                "language": "zh-CN",
            },
            "voice": {"provider": "edge-tts", "voice": "zh-CN-XiaoxiaoNeural"},
            "render": {"fps": 24, "burn_subtitles": True, "auto_edit": True},
            "capabilities": {
                "browser": {
                    "required": False,
                    "target_url": "http://localhost:8000",
                    "viewport": {"width": 1920, "height": 1080},
                    "checks": ["page_load"],
                    "recording": {"enabled": False, "duration_seconds": 10, "output": "assets/browser/demo.mp4"},
                }
            },
            "upload": {"enabled": False, "confirmation": "required"},
        }

        self.assertEqual(validate_pipeline(pipeline), [])

    def test_validate_pipeline_reports_invalid_config(self):
        pipeline = {
            "project": {"name": "", "type": "general_demo"},
            "source": {"type": "user_request"},
            "video": {
                "platform": "youtube",
                "aspect_ratio": "16:9",
                "resolution": "1920x1080",
                "target_duration": 0,
                "language": "",
            },
            "render": {"fps": "24", "burn_subtitles": True, "auto_edit": "yes"},
            "capabilities": {
                "browser": {
                    "required": False,
                    "target_url": "",
                    "checks": [],
                    "viewport": {"width": 0, "height": "1080"},
                    "recording": {"enabled": True},
                }
            },
            "upload": {"enabled": True, "confirmation": "optional"},
        }

        errors = validate_pipeline(pipeline)

        self.assertIn("project.name must be a non-empty string", errors)
        self.assertIn("source.value must be a non-empty string", errors)
        self.assertIn("video.target_duration must be a positive integer", errors)
        self.assertIn("video.language must be a non-empty string", errors)
        self.assertIn("render.fps must be a positive integer", errors)
        self.assertIn("render.auto_edit must be true or false", errors)
        self.assertIn("capabilities.browser.target_url must be a non-empty string", errors)
        self.assertIn("capabilities.browser.checks must be a non-empty list of strings", errors)
        self.assertIn("capabilities.browser.viewport.width must be a positive integer", errors)
        self.assertIn("capabilities.browser.viewport.height must be a positive integer", errors)
        self.assertIn("capabilities.browser.recording.duration_seconds must be a positive integer", errors)
        self.assertIn("upload.confirmation must be required when upload.enabled is true", errors)

    def test_completed_pipeline_clears_next_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline_path = write_project_files(root, gui_required=False)
            ctx = create_run(root, run_id="pipeline-run")
            initialize_pipeline_run(ctx, pipeline_path)
            approve_gate(ctx, "brief", summary="brief ok")
            advance_pipeline(ctx)
            approve_gate(ctx, "plan", summary="plan ok")

            originals = (
                pipeline_module.generate_voice,
                pipeline_module.render,
                pipeline_module.qa,
                pipeline_module.package,
            )
            pipeline_module.generate_voice = fake_generate_voice
            pipeline_module.render = fake_render
            pipeline_module.qa = fake_qa
            pipeline_module.package = fake_package
            try:
                result = pipeline_module.advance_pipeline(ctx)
            finally:
                (
                    pipeline_module.generate_voice,
                    pipeline_module.render,
                    pipeline_module.qa,
                    pipeline_module.package,
                ) = originals

            self.assertEqual(result["status"], "package_ready")
            self.assertEqual(result["next_action"], "")


def write_project_files(root: Path, gui_required: bool, browser_target_url: str = "") -> Path:
    (root / "templates" / "briefs").mkdir(parents=True)
    (root / "templates" / "storyboards").mkdir(parents=True)
    (root / "templates" / "briefs" / "general_demo.yml").write_text(
        "goal: ''\naudience: ''\nplatform: youtube\nduration: 60\nupload:\n  enabled: false\n",
        encoding="utf-8",
    )
    (root / "templates" / "storyboards" / "general_demo.yml").write_text(
        "title: ''\ntarget_duration: 60\naspect_ratio: '16:9'\nsections: []\n",
        encoding="utf-8",
    )
    pipeline_path = root / "pipeline.yml"
    lines = [
        "project:",
        "  name: AI Video Maker",
        "  type: general_demo",
        "source:",
        "  type: user_request",
        "  value: 介绍 AI Video Maker",
        "video:",
        "  platform: youtube",
        "  target_duration: 60",
        "  language: zh-CN",
        "capabilities:",
        "  browser:",
        f"    required: {str(gui_required).lower()}",
    ]
    if browser_target_url:
        lines.append(f"    target_url: {browser_target_url}")
    lines.extend(
        [
            "script:",
            "  narration: |",
            "    测试旁白。",
            "upload:",
            "  enabled: false",
            "",
        ]
    )
    pipeline_path.write_text("\n".join(lines), encoding="utf-8")
    return pipeline_path


def fake_generate_voice(ctx):
    ctx.path("audio/narration.mp3").write_text("voice", encoding="utf-8")
    ctx.update_state("voice_ready", "voice")


def fake_render(ctx):
    ctx.path("render/final_16x9.mp4").write_text("video", encoding="utf-8")
    ctx.update_state("render_ready", "render")


def fake_qa(ctx):
    ctx.path("qa/report.md").write_text("# QA\n", encoding="utf-8")
    ctx.update_state("qa_ready", "qa")


def fake_package(ctx):
    ctx.path("package/video.mp4").write_text("video", encoding="utf-8")
    ctx.update_state("package_ready", "package")


if __name__ == "__main__":
    unittest.main()
