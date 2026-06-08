import tempfile
import unittest
from pathlib import Path

import ai_video_maker.qa_revision_workflow as qa_revision_module
from ai_video_maker.context import create_run
from ai_video_maker.io import read_yaml, write_yaml
from ai_video_maker.qa_revision_workflow import generate_qa_revision


class QaRevisionWorkflowTests(unittest.TestCase):
    def test_generate_qa_revision_requires_edit_render_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_run(Path(tmp), run_id="qa-run")

            with self.assertRaises(FileNotFoundError):
                generate_qa_revision(ctx)

    def test_generate_qa_revision_writes_success_outputs_and_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_qa_run(Path(tmp), captions="hello")
            originals = (qa_revision_module._ffprobe, qa_revision_module._extract_screenshot)
            qa_revision_module._ffprobe = fake_ffprobe
            qa_revision_module._extract_screenshot = fake_extract_screenshot
            try:
                handoff = generate_qa_revision(ctx)
            finally:
                qa_revision_module._ffprobe, qa_revision_module._extract_screenshot = originals

            self.assertEqual(handoff["skill"], "qa-revision")
            self.assertEqual(handoff["status"], "ready_for_review")
            self.assertEqual(handoff["next_skill_suggestion"], "publish-package")
            self.assertTrue(ctx.path("qa/report.md").exists())
            self.assertTrue(ctx.path("qa/ffprobe.json").exists())
            self.assertTrue(ctx.path("qa/screenshots/frame_6s.png").exists())
            self.assertEqual(read_yaml(ctx.path("qa/handoff.qa-revision.yml"))["skill"], "qa-revision")
            self.assertEqual(ctx.state()["status"], "qa_revision_ready")

    def test_generate_qa_revision_routes_missing_video_to_edit_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_qa_run(Path(tmp), captions="hello")
            ctx.path("render/final_16x9.mp4").unlink()

            handoff = generate_qa_revision(ctx)

            self.assertEqual(handoff["status"], "needs_revision")
            self.assertEqual(handoff["revision_skill_suggestion"], "edit-render")
            self.assertTrue(ctx.path("qa/report.md").exists())
            self.assertEqual(ctx.state()["status"], "qa_revision_needs_revision")

    def test_generate_qa_revision_routes_empty_captions_to_voice_subtitle(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_qa_run(Path(tmp), captions="")
            originals = (qa_revision_module._ffprobe, qa_revision_module._extract_screenshot)
            qa_revision_module._ffprobe = fake_ffprobe
            qa_revision_module._extract_screenshot = fake_extract_screenshot
            try:
                handoff = generate_qa_revision(ctx)
            finally:
                qa_revision_module._ffprobe, qa_revision_module._extract_screenshot = originals

            self.assertEqual(handoff["status"], "needs_revision")
            self.assertEqual(handoff["revision_skill_suggestion"], "voice-subtitle")


def create_qa_run(root: Path, *, captions: str):
    ctx = create_run(root, run_id="qa-run")
    write_yaml(ctx.path("render/handoff.edit-render.yml"), {"skill": "edit-render", "status": "ready_for_review"})
    ctx.path("render/final_16x9.mp4").write_bytes(b"video")
    ctx.path("subtitles/captions.srt").write_text(captions, encoding="utf-8")
    return ctx


def fake_ffprobe(video: Path):
    return {
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080},
            {"codec_type": "audio", "codec_name": "aac"},
        ],
        "format": {"duration": "10.0"},
    }


def fake_extract_screenshot(video: Path, screenshot: Path) -> bool:
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"png")
    return True


if __name__ == "__main__":
    unittest.main()
