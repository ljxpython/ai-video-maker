import tempfile
import unittest
from pathlib import Path

import ai_video_maker.pipeline as pipeline_module
from ai_video_maker.context import create_run
from ai_video_maker.io import read_yaml
from ai_video_maker.pipeline import advance_pipeline, initialize_pipeline_run, status_summary
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
            self.assertTrue(ctx.path("script/narration.zh.txt").exists())

            artifacts = read_yaml(ctx.artifacts_path)
            ids = {item["id"] for item in artifacts["artifacts"]}
            self.assertIn("pipeline", ids)
            self.assertIn("asset_plan", ids)

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


def write_project_files(root: Path, gui_required: bool) -> Path:
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
    pipeline_path.write_text(
        "\n".join(
            [
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
                "script:",
                "  narration: |",
                "    测试旁白。",
                "upload:",
                "  enabled: false",
                "",
            ]
        ),
        encoding="utf-8",
    )
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
