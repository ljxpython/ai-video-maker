import tempfile
import unittest
from pathlib import Path

from ai_video_maker.context import create_run
from ai_video_maker.io import write_yaml
from ai_video_maker.revision_workflow import generate_revision_plan


class RevisionWorkflowTests(unittest.TestCase):
    def test_generate_revision_plan_from_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_run(Path(tmp), run_id="revision-run")
            write_yaml(ctx.path("qa/issues.yml"), {"version": 1, "issues": [{"id": "audio_stream", "message": "missing audio", "revision_skill_suggestion": "voice-subtitle"}]})

            plan = generate_revision_plan(ctx, "audio_stream")

            self.assertEqual(plan["revision_skill"], "voice-subtitle")
            self.assertTrue(ctx.path(f"revisions/{plan['revision_id']}.yml").exists())


if __name__ == "__main__":
    unittest.main()
