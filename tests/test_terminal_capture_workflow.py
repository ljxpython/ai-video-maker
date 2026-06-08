import tempfile
import unittest
from pathlib import Path

from ai_video_maker.context import create_run
from ai_video_maker.io import read_yaml, write_yaml
from ai_video_maker.stages import approve_gate
from ai_video_maker.terminal_actions import validate_safe_command
from ai_video_maker.terminal_capture_workflow import generate_terminal_capture


class TerminalCaptureWorkflowTests(unittest.TestCase):
    def test_blocks_dangerous_command(self):
        with self.assertRaises(ValueError):
            validate_safe_command("rm -rf output")

    def test_requires_execution_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_terminal_run(Path(tmp))

            with self.assertRaises(PermissionError):
                generate_terminal_capture(ctx)

    def test_generates_logs_cards_and_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_terminal_run(Path(tmp))
            approve_gate(ctx, "execution")

            handoff = generate_terminal_capture(ctx)

            self.assertEqual(handoff["skill"], "terminal-capture")
            self.assertEqual(handoff["status"], "ready_for_review")
            self.assertTrue(ctx.path("qa/terminal_capture.md").exists())
            self.assertTrue(ctx.path("assets/terminal/cards/check_python.png").exists())
            self.assertEqual(read_yaml(ctx.path("assets/terminal/handoff.terminal-capture.yml"))["skill"], "terminal-capture")


def create_terminal_run(root: Path):
    ctx = create_run(root, run_id="terminal-run")
    write_yaml(
        ctx.path("script/terminal_actions.yml"),
        {
            "version": 1,
            "working_directory": ".",
            "commands": [
                {"id": "check_python", "title": "Check Python", "command": "python --version"},
            ],
        },
    )
    return ctx


if __name__ == "__main__":
    unittest.main()
