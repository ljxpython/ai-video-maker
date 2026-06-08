import tempfile
import unittest
from pathlib import Path

import ai_video_maker.edit_render_workflow as edit_render_module
from ai_video_maker.context import create_run
from ai_video_maker.io import read_yaml, write_yaml
from ai_video_maker.edit_render_workflow import generate_edit_render


class EditRenderWorkflowTests(unittest.TestCase):
    def test_generate_edit_render_requires_voice_subtitle_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_run(Path(tmp), run_id="render-run")

            with self.assertRaises(FileNotFoundError):
                generate_edit_render(ctx)

    def test_generate_edit_render_writes_outputs_and_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_edit_render_run(Path(tmp), with_browser=False)
            originals = (edit_render_module.render_mixed_video, edit_render_module.run_command)
            edit_render_module.render_mixed_video = fake_render_mixed_video
            edit_render_module.run_command = fake_auto_editor
            try:
                handoff = generate_edit_render(ctx)
            finally:
                edit_render_module.render_mixed_video, edit_render_module.run_command = originals

            self.assertEqual(handoff["skill"], "edit-render")
            self.assertEqual(handoff["next_skill_suggestion"], "qa-revision")
            self.assertTrue(ctx.path("render/draft.mp4").exists())
            self.assertTrue(ctx.path("render/final_16x9.mp4").exists())
            self.assertEqual(read_yaml(ctx.path("render/handoff.edit-render.yml"))["skill"], "edit-render")
            self.assertEqual(ctx.state()["status"], "edit_render_ready")

    def test_generate_edit_render_uses_browser_recording_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_edit_render_run(Path(tmp), with_browser=True)
            calls = []
            originals = (edit_render_module.render_mixed_video, edit_render_module.run_command)
            edit_render_module.render_mixed_video = lambda **kwargs: fake_render_mixed_video_with_calls(kwargs, calls)
            edit_render_module.run_command = fake_auto_editor
            try:
                generate_edit_render(ctx)
            finally:
                edit_render_module.render_mixed_video, edit_render_module.run_command = originals

            self.assertEqual(calls[0]["browser_recording_path"], ctx.path("assets/browser/demo.webm"))


def create_edit_render_run(root: Path, *, with_browser: bool):
    ctx = create_run(root, run_id="render-run")
    write_yaml(
        ctx.path("subtitles/handoff.voice-subtitle.yml"),
        {"skill": "voice-subtitle", "status": "ready_for_review"},
    )
    write_yaml(
        ctx.path("plan/storyboard.yml"),
        {
            "title": "Demo",
            "target_duration": 20,
            "aspect_ratio": "16:9",
            "sections": [
                {"id": "hook", "duration": 5, "visual": "title", "narration": "intro"},
                {"id": "steps", "duration": 15, "visual": "demo", "narration": "steps"},
            ],
        },
    )
    ctx.path("audio/narration.mp3").write_text("audio", encoding="utf-8")
    ctx.path("subtitles/captions.srt").write_text("1\n00:00:00,000 --> 00:00:02,000\nhello\n", encoding="utf-8")
    ctx.path("pipeline.yml").write_text("render:\n  auto_edit: true\n  fps: 24\n", encoding="utf-8")
    if with_browser:
        ctx.path("assets/browser/demo.webm").parent.mkdir(parents=True, exist_ok=True)
        ctx.path("assets/browser/demo.webm").write_text("video", encoding="utf-8")
        write_yaml(
            ctx.path("assets/browser/handoff.browser-capture.yml"),
            {"outputs": ["assets/browser/demo.webm"]},
        )
    return ctx


def fake_render_mixed_video(**kwargs):
    kwargs["output_path"].write_text("draft", encoding="utf-8")
    return kwargs["output_path"]


def fake_render_mixed_video_with_calls(kwargs, calls):
    calls.append(kwargs)
    kwargs["output_path"].write_text("draft", encoding="utf-8")
    return kwargs["output_path"]


def fake_auto_editor(args):
    output = Path(args[args.index("-o") + 1])
    output.write_text("final", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
