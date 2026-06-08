import tempfile
import unittest
from pathlib import Path

from ai_video_maker.context import create_run
from ai_video_maker.gui_capture_workflow import generate_chrome_operation_plan, record_chrome_operation_result
from ai_video_maker.stages import approve_gate


class GuiCaptureWorkflowTests(unittest.TestCase):
    def test_chrome_plan_writes_operation_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_run(Path(tmp), run_id="chrome-run")

            plan = generate_chrome_operation_plan(ctx)

            self.assertEqual(plan["tool"], "$chrome")
            self.assertTrue(ctx.path("plan/chrome_operation.yml").exists())

    def test_record_chrome_result_requires_execution_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = create_run(root, run_id="chrome-run")
            screenshot = root / "shot.png"
            screenshot.write_bytes(b"png")

            with self.assertRaises(PermissionError):
                record_chrome_operation_result(ctx, screenshot=screenshot)

            approve_gate(ctx, "execution")
            handoff = record_chrome_operation_result(ctx, screenshot=screenshot)
            self.assertEqual(handoff["skill"], "chrome-capture")


if __name__ == "__main__":
    unittest.main()
