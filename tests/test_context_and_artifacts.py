import tempfile
import unittest
from pathlib import Path

from ai_video_maker.artifacts import record_artifact
from ai_video_maker.context import RUN_DIRS, create_run, load_run
from ai_video_maker.io import read_json, read_yaml


class ContextAndArtifactTests(unittest.TestCase):
    def test_create_run_initializes_structure_and_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = create_run(root, run_id="unit-run")

            self.assertEqual(ctx.run_id, "unit-run")
            for item in RUN_DIRS:
                self.assertTrue((ctx.run_dir / item).exists(), item)

            state = read_json(ctx.state_path)
            self.assertEqual(state["run_id"], "unit-run")
            self.assertEqual(state["status"], "created")
            self.assertEqual(state["current_stage"], "new")

            approvals = read_yaml(ctx.approvals_path)
            self.assertEqual(approvals["brief"]["status"], "pending")
            self.assertEqual(approvals["publish"]["status"], "pending")

            artifacts = read_yaml(ctx.artifacts_path)
            self.assertEqual(artifacts["run_id"], "unit-run")
            self.assertEqual(artifacts["artifacts"], [])

    def test_create_run_refuses_existing_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_run(root, run_id="unit-run")
            with self.assertRaises(FileExistsError):
                create_run(root, run_id="unit-run")

    def test_create_run_overwrite_removes_stale_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = create_run(root, run_id="unit-run")
            stale = ctx.path("render/final_16x9.mp4")
            stale.write_text("old video", encoding="utf-8")

            create_run(root, run_id="unit-run", overwrite=True)

            self.assertFalse(stale.exists())

    def test_load_run_and_record_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = create_run(root, run_id="unit-run")
            loaded = load_run(root, "runs/unit-run")
            self.assertEqual(loaded.run_dir, ctx.run_dir)

            artifact = ctx.path("script/narration.zh.txt")
            artifact.write_text("hello", encoding="utf-8")
            record_artifact(ctx, "narration", "text", artifact, "script")

            data = read_yaml(ctx.artifacts_path)
            self.assertEqual(len(data["artifacts"]), 1)
            self.assertEqual(data["artifacts"][0]["path"], "script/narration.zh.txt")

            record_artifact(ctx, "narration", "text", artifact, "updated")
            data = read_yaml(ctx.artifacts_path)
            self.assertEqual(len(data["artifacts"]), 1)
            self.assertEqual(data["artifacts"][0]["stage"], "updated")


if __name__ == "__main__":
    unittest.main()
