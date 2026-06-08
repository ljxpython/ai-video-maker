import tempfile
import unittest
from pathlib import Path

from ai_video_maker.browser_adapter import record_browser_preflight_result
from ai_video_maker.context import create_run
from ai_video_maker.io import read_json, read_yaml, write_yaml
from ai_video_maker.stages import approve_gate


class BrowserAdapterTests(unittest.TestCase):
    def test_record_browser_result_requires_execution_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = create_browser_run(root)
            screenshot = root / "screenshot.png"
            screenshot.write_bytes(b"fake image")

            with self.assertRaises(PermissionError):
                record_browser_preflight_result(
                    ctx,
                    screenshot=screenshot,
                    current_url="http://localhost:8000",
                    title="AI Video Maker Browser Demo",
                    non_blank=True,
                )

    def test_record_browser_result_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = create_browser_run(root)
            approve_gate(ctx, "execution", summary="execution ok")
            screenshot = root / "screenshot.png"
            screenshot.write_bytes(b"fake image")

            result = record_browser_preflight_result(
                ctx,
                screenshot=screenshot,
                current_url="http://localhost:8000",
                title="AI Video Maker Browser Demo",
                non_blank=True,
            )

            self.assertEqual(result["status"], "passed")
            self.assertTrue(ctx.path("assets/browser/preflight_screenshot.png").exists())
            self.assertTrue(ctx.path("qa/browser_preflight.md").exists())
            self.assertEqual(read_json(ctx.path("qa/browser_preflight.json"))["status"], "passed")
            self.assertEqual(ctx.state()["status"], "browser_preflight_ready")

            artifacts = read_yaml(ctx.artifacts_path)
            ids = {item["id"] for item in artifacts["artifacts"]}
            self.assertIn("browser_preflight_result", ids)
            self.assertIn("browser_preflight_report", ids)
            self.assertIn("browser_preflight_screenshot", ids)


def create_browser_run(root: Path):
    ctx = create_run(root, run_id="browser-run")
    write_yaml(
        ctx.path("plan/browser_preflight.yml"),
        {
            "target_url": "http://localhost:8000",
            "target_kind": "local_web",
        },
    )
    return ctx


if __name__ == "__main__":
    unittest.main()
