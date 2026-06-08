import tempfile
import unittest
from pathlib import Path

from ai_video_maker.context import create_run
from ai_video_maker.io import read_yaml
from ai_video_maker.stages import approve_gate, initialize_run_files


class StageTests(unittest.TestCase):
    def test_initialize_run_files_creates_brief_plan_and_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "templates" / "briefs").mkdir(parents=True)
            (root / "templates" / "storyboards").mkdir(parents=True)
            (root / "templates" / "briefs" / "general_demo.yml").write_text(
                "goal: ''\naudience: ''\nupload:\n  enabled: false\n",
                encoding="utf-8",
            )
            (root / "templates" / "storyboards" / "general_demo.yml").write_text(
                "title: ''\nsections: []\n",
                encoding="utf-8",
            )

            ctx = create_run(root, run_id="stage-run")
            initialize_run_files(ctx)

            brief = read_yaml(ctx.path("brief.yml"))
            self.assertEqual(brief["goal"], "介绍 AI Video Maker 项目自己")
            self.assertEqual(brief["platform"], "youtube")
            self.assertTrue(ctx.path("script/narration.zh.txt").read_text(encoding="utf-8"))

            artifacts = read_yaml(ctx.artifacts_path)
            artifact_ids = {item["id"] for item in artifacts["artifacts"]}
            self.assertIn("brief", artifact_ids)
            self.assertIn("storyboard", artifact_ids)
            self.assertIn("narration_script", artifact_ids)

    def test_approve_gate_updates_approvals_and_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = create_run(root, run_id="approval-run")

            approve_gate(ctx, "plan", summary="unit approved")

            approvals = read_yaml(ctx.approvals_path)
            self.assertEqual(approvals["plan"]["status"], "approved")
            self.assertEqual(approvals["plan"]["summary"], "unit approved")
            self.assertEqual(ctx.state()["status"], "plan_approved")


if __name__ == "__main__":
    unittest.main()
