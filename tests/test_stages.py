import tempfile
import unittest
from pathlib import Path

from ai_video_maker.context import create_run
from ai_video_maker.io import read_yaml
import ai_video_maker.stages as stages_module
from ai_video_maker.stages import approve_gate, initialize_run_files, vtt_to_srt


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

    def test_generate_voice_uses_pipeline_voice_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = create_run(root, run_id="voice-run")
            ctx.path("script/narration.zh.txt").write_text("hello", encoding="utf-8")
            ctx.path("pipeline.yml").write_text(
                "\n".join(
                    [
                        "voice:",
                        "  voice: zh-CN-YunxiNeural",
                        "  rate: -10%",
                        "  pitch: +2Hz",
                        "  volume: +5%",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            calls = []
            original = stages_module.run_command
            stages_module.run_command = lambda args: fake_edge_tts(args, calls)
            try:
                stages_module.generate_voice(ctx)
            finally:
                stages_module.run_command = original

            command = calls[0]
            self.assertIn("zh-CN-YunxiNeural", command)
            self.assertIn("-10%", command)
            self.assertIn("+2Hz", command)
            self.assertIn("+5%", command)
            self.assertTrue(ctx.path("subtitles/captions.srt").exists())
            self.assertIn("00:00:00,000", ctx.path("subtitles/captions.srt").read_text(encoding="utf-8"))

    def test_generate_voice_falls_back_to_subtitle_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = create_run(root, run_id="voice-run")
            ctx.path("script/narration.zh.txt").write_text("hello", encoding="utf-8")
            ctx.path("script/subtitle_draft.srt").write_text("1\n00:00:00,000 --> 00:00:02,000\nhello\n", encoding="utf-8")

            original = stages_module.run_command
            stages_module.run_command = lambda args: fake_edge_tts_empty_subtitle(args)
            try:
                stages_module.generate_voice(ctx)
            finally:
                stages_module.run_command = original

            self.assertEqual(
                ctx.path("subtitles/captions.srt").read_text(encoding="utf-8"),
                "1\n00:00:00,000 --> 00:00:02,000\nhello\n",
            )

    def test_render_can_skip_auto_editor_from_pipeline_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = create_run(root, run_id="render-run")
            ctx.path("audio/narration.mp3").write_text("audio", encoding="utf-8")
            ctx.path("subtitles/captions.srt").write_text("", encoding="utf-8")
            ctx.path("pipeline.yml").write_text(
                "\n".join(
                    [
                        "project:",
                        "  name: Configured Demo",
                        "video:",
                        "  style: 测试风格",
                        "render:",
                        "  fps: 12",
                        "  auto_edit: false",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            commands = []
            render_calls = []
            originals = (stages_module.render_video, stages_module.run_command)
            stages_module.render_video = lambda **kwargs: fake_render_video(kwargs, render_calls)
            stages_module.run_command = lambda args: commands.append(args)
            try:
                stages_module.render(ctx)
            finally:
                stages_module.render_video, stages_module.run_command = originals

            self.assertEqual(commands, [])
            self.assertEqual(render_calls[0]["title"], "Configured Demo")
            self.assertEqual(render_calls[0]["fps"], 12)
            self.assertTrue(ctx.path("render/final_16x9.mp4").exists())


def fake_edge_tts(args, calls):
    calls.append(args)
    media = Path(args[args.index("--write-media") + 1])
    subtitles = Path(args[args.index("--write-subtitles") + 1])
    media.write_text("audio", encoding="utf-8")
    subtitles.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nhello\n", encoding="utf-8")


def fake_edge_tts_empty_subtitle(args):
    media = Path(args[args.index("--write-media") + 1])
    subtitles = Path(args[args.index("--write-subtitles") + 1])
    media.write_text("audio", encoding="utf-8")
    subtitles.write_text("WEBVTT\n", encoding="utf-8")


class SubtitleConversionTests(unittest.TestCase):
    def test_vtt_to_srt_converts_timestamps(self):
        srt = vtt_to_srt("WEBVTT\n\n00:00:00.000 --> 00:00:02.500\nhello\n")

        self.assertEqual(srt, "1\n00:00:00,000 --> 00:00:02,500\nhello\n")

    def test_vtt_to_srt_accepts_cue_ids(self):
        srt = vtt_to_srt("WEBVTT\n\n1\n00:00:00.100 --> 00:00:02.500\nhello\n")

        self.assertEqual(srt, "1\n00:00:00,100 --> 00:00:02,500\nhello\n")

    def test_vtt_to_srt_accepts_comma_milliseconds(self):
        srt = vtt_to_srt("WEBVTT\n\n1\n00:00:00,100 --> 00:00:02,500\nhello\n")

        self.assertEqual(srt, "1\n00:00:00,100 --> 00:00:02,500\nhello\n")

    def test_vtt_to_srt_removes_overlaps(self):
        srt = vtt_to_srt(
            "WEBVTT\n\n"
            "00:00:00.000 --> 00:00:02.500\nfirst\n\n"
            "00:00:02.400 --> 00:00:04.000\nsecond\n"
        )

        self.assertIn("00:00:00,000 --> 00:00:02,400", srt)
        self.assertIn("00:00:02,400 --> 00:00:04,000", srt)


def fake_render_video(kwargs, calls):
    calls.append(kwargs)
    output = kwargs["output_path"]
    output.write_text("video", encoding="utf-8")
    return output


if __name__ == "__main__":
    unittest.main()
