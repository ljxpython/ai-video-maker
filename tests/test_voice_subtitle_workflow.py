import tempfile
import unittest
from pathlib import Path

import ai_video_maker.voice_subtitle_workflow as voice_subtitle_module
from ai_video_maker.context import create_run
from ai_video_maker.io import read_yaml, write_yaml
from ai_video_maker.voice_subtitle_workflow import generate_voice_subtitle


class VoiceSubtitleWorkflowTests(unittest.TestCase):
    def test_generate_voice_subtitle_requires_video_script_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_run(Path(tmp), run_id="voice-run")

            with self.assertRaises(FileNotFoundError):
                generate_voice_subtitle(ctx)

    def test_generate_voice_subtitle_writes_outputs_and_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_voice_subtitle_run(Path(tmp))
            original = voice_subtitle_module.generate_voice
            voice_subtitle_module.generate_voice = fake_generate_voice
            try:
                handoff = generate_voice_subtitle(ctx)
            finally:
                voice_subtitle_module.generate_voice = original

            self.assertEqual(handoff["skill"], "voice-subtitle")
            self.assertEqual(handoff["status"], "ready_for_review")
            self.assertEqual(handoff["next_skill_suggestion"], "edit-render")
            self.assertTrue(ctx.path("audio/narration.mp3").exists())
            self.assertTrue(ctx.path("subtitles/captions.srt").exists())
            self.assertEqual(read_yaml(ctx.path("subtitles/handoff.voice-subtitle.yml"))["skill"], "voice-subtitle")
            self.assertEqual(ctx.state()["status"], "voice_subtitle_ready")


def create_voice_subtitle_run(root: Path):
    ctx = create_run(root, run_id="voice-run")
    write_yaml(
        ctx.path("script/handoff.video-script.yml"),
        {
            "skill": "video-script",
            "status": "ready_for_review",
            "outputs": ["script/narration.zh.txt"],
        },
    )
    ctx.path("script/narration.zh.txt").write_text("测试旁白。\n", encoding="utf-8")
    return ctx


def fake_generate_voice(ctx):
    ctx.path("audio/narration.mp3").write_text("audio", encoding="utf-8")
    ctx.path("subtitles/captions.srt").write_text("1\n00:00:00,000 --> 00:00:02,000\n测试旁白。\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
