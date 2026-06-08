import tempfile
import unittest
from pathlib import Path

import ai_video_maker.browser_capture_workflow as browser_capture_module
from ai_video_maker.browser_capture_workflow import generate_browser_capture
from ai_video_maker.context import create_run
from ai_video_maker.io import read_yaml, write_yaml
from ai_video_maker.stages import approve_gate


class BrowserCaptureWorkflowTests(unittest.TestCase):
    def test_generate_browser_capture_requires_execution_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_browser_capture_run(Path(tmp))

            with self.assertRaises(PermissionError):
                generate_browser_capture(ctx)

    def test_generate_browser_capture_writes_outputs_and_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_browser_capture_run(Path(tmp))
            approve_gate(ctx, "execution", summary="ok to capture browser")
            original = browser_capture_module._capture_with_playwright
            browser_capture_module._capture_with_playwright = fake_capture
            try:
                handoff = generate_browser_capture(ctx)
            finally:
                browser_capture_module._capture_with_playwright = original

            self.assertEqual(handoff["skill"], "browser-capture")
            self.assertEqual(handoff["status"], "ready_for_review")
            self.assertEqual(handoff["next_skill_suggestion"], "voice-subtitle")
            self.assertTrue(ctx.path("assets/browser/demo.webm").exists())
            self.assertTrue(ctx.path("assets/browser/screenshot.png").exists())
            self.assertTrue(ctx.path("qa/browser_capture.md").exists())
            self.assertEqual(read_yaml(ctx.path("assets/browser/handoff.browser-capture.yml"))["skill"], "browser-capture")
            self.assertEqual(ctx.state()["status"], "browser_capture_ready")


def create_browser_capture_run(root: Path):
    ctx = create_run(root, run_id="browser-capture-run")
    write_yaml(
        ctx.path("plan/browser_preflight.yml"),
        {
            "target_url": "http://localhost:8000",
            "target_kind": "local_web",
            "viewport": {"width": 1920, "height": 1080},
            "recording": {"enabled": True, "duration_seconds": 3, "output": "assets/browser/demo.webm"},
        },
    )
    return ctx


def fake_capture(*, target_url, screenshot, recording, viewport, duration_seconds):
    screenshot.write_bytes(b"png")
    recording.write_bytes(b"webm")
    return {
        "passed": True,
        "target_url": target_url,
        "current_url": target_url,
        "title": "Demo",
        "duration_seconds": duration_seconds,
        "screenshot_non_blank": True,
        "recording_non_empty": True,
    }


if __name__ == "__main__":
    unittest.main()
