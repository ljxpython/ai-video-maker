import tempfile
import unittest
from pathlib import Path

from ai_video_maker.context import create_run
from ai_video_maker.io import read_yaml, write_yaml
from ai_video_maker.script_workflow import generate_video_script
from ai_video_maker.stages import approve_gate


class ScriptWorkflowTests(unittest.TestCase):
    def test_generate_video_script_requires_plan_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_script_run(Path(tmp))

            with self.assertRaises(PermissionError):
                generate_video_script(ctx)

    def test_generate_video_script_writes_outputs_and_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_script_run(Path(tmp))
            approve_gate(ctx, "plan", summary="plan ok")

            handoff = generate_video_script(ctx)

            self.assertEqual(handoff["status"], "ready_for_review")
            self.assertEqual(handoff["next_skill_suggestion"], "voice-subtitle")
            self.assertTrue(ctx.path("script/screen_actions.md").exists())
            self.assertTrue(ctx.path("script/subtitle_draft.srt").exists())
            self.assertTrue(ctx.path("script/shot_notes.md").exists())
            self.assertEqual(read_yaml(ctx.path("script/handoff.video-script.yml"))["skill"], "video-script")
            self.assertIn("00:00:00,000", ctx.path("script/subtitle_draft.srt").read_text(encoding="utf-8"))
            self.assertIn("第一句。", ctx.path("script/subtitle_draft.srt").read_text(encoding="utf-8"))

    def test_generate_video_script_keeps_ascii_tokens_in_subtitles(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_script_run(Path(tmp))
            ctx.path("script/narration.zh.txt").write_text(
                "用户通过 ai-video-maker orchestrator 调用 video-script 继续制作。\n",
                encoding="utf-8",
            )
            approve_gate(ctx, "plan", summary="plan ok")

            generate_video_script(ctx)

            subtitle = ctx.path("script/subtitle_draft.srt").read_text(encoding="utf-8")
            self.assertIn("ai-video-maker", subtitle)
            self.assertIn("orchestrator", subtitle)


def create_script_run(root: Path):
    ctx = create_run(root, run_id="script-run")
    write_yaml(
        ctx.path("plan/storyboard.yml"),
        {
            "title": "Demo",
            "target_duration": 20,
            "aspect_ratio": "16:9",
            "sections": [
                {
                    "id": "hook",
                    "duration": 8,
                    "purpose": "show value",
                    "visual": "title card",
                    "narration": "intro",
                }
            ],
        },
    )
    write_yaml(ctx.path("plan/capability_plan.yml"), {"required": []})
    ctx.path("script/narration.zh.txt").write_text("第一句。\n第二句。\n", encoding="utf-8")
    return ctx


if __name__ == "__main__":
    unittest.main()
