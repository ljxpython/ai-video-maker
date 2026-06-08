import tempfile
import unittest
from pathlib import Path

from ai_video_maker.context import create_run
from ai_video_maker.io import read_yaml, write_yaml
from ai_video_maker.orchestrator import generate_next
from ai_video_maker.stages import approve_gate


class OrchestratorTests(unittest.TestCase):
    def test_next_recommends_video_brief_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_run(Path(tmp), run_id="next-run")

            result = generate_next(ctx)

            self.assertEqual(result["next_skill_suggestion"], "video-brief")
            self.assertTrue(ctx.path("orchestrator/next.yml").exists())

    def test_next_stops_at_brief_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_run(Path(tmp), run_id="next-run")
            ctx.path("brief.yml").write_text("goal: demo\n", encoding="utf-8")

            result = generate_next(ctx)

            self.assertEqual(result["next_gate"], "brief")
            self.assertTrue(result["user_action_required"])

    def test_next_uses_handoff_suggestion_after_soft_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_run(Path(tmp), run_id="next-run")
            ctx.path("brief.yml").write_text("goal: demo\n", encoding="utf-8")
            approve_gate(ctx, "brief")
            ctx.path("plan/storyboard.yml").write_text("sections: []\n", encoding="utf-8")
            approve_gate(ctx, "plan")
            write_yaml(ctx.path("script/handoff.video-script.yml"), {"skill": "video-script", "status": "ready_for_review", "next_skill_suggestion": "voice-subtitle"})

            result = generate_next(ctx)

            self.assertEqual(result["next_skill_suggestion"], "voice-subtitle")

    def test_publish_package_stops_at_upload_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_run(Path(tmp), run_id="next-run")
            ctx.path("brief.yml").write_text("goal: demo\n", encoding="utf-8")
            approve_gate(ctx, "brief")
            ctx.path("plan/storyboard.yml").write_text("sections: []\n", encoding="utf-8")
            approve_gate(ctx, "plan")
            write_yaml(ctx.path("script/handoff.video-script.yml"), {"skill": "video-script", "status": "ready_for_review", "next_skill_suggestion": "voice-subtitle"})
            write_yaml(ctx.path("subtitles/handoff.voice-subtitle.yml"), {"skill": "voice-subtitle", "status": "ready_for_review", "next_skill_suggestion": "edit-render"})
            write_yaml(ctx.path("render/handoff.edit-render.yml"), {"skill": "edit-render", "status": "ready_for_review", "next_skill_suggestion": "qa-revision"})
            write_yaml(ctx.path("qa/handoff.qa-revision.yml"), {"skill": "qa-revision", "status": "ready_for_review", "next_skill_suggestion": "publish-package"})
            write_yaml(ctx.path("package/handoff.publish-package.yml"), {"skill": "publish-package", "status": "ready_for_gate", "next_gate": "upload"})

            result = generate_next(ctx)

            self.assertEqual(result["next_gate"], "upload")
            self.assertIsNone(result["next_skill_suggestion"])


if __name__ == "__main__":
    unittest.main()
