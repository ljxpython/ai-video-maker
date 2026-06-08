import tempfile
import unittest
from pathlib import Path

from ai_video_maker.context import create_run
from ai_video_maker.io import read_yaml, write_yaml
from ai_video_maker.youtube_upload_workflow import generate_youtube_upload


class YoutubeUploadWorkflowTests(unittest.TestCase):
    def test_dry_run_writes_plan_and_does_not_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_package_run(Path(tmp))

            handoff = generate_youtube_upload(ctx, mode="dry-run")

            self.assertEqual(handoff["status"], "waiting_for_gate")
            self.assertEqual(handoff["next_gate"], "upload")
            self.assertFalse(handoff["safety"]["network_requests_performed"])
            self.assertTrue(ctx.path("upload/youtube_upload_plan.yml").exists())

    def test_execute_upload_requires_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_package_run(Path(tmp))

            with self.assertRaises(PermissionError):
                generate_youtube_upload(ctx, mode="execute-upload")


def create_package_run(root: Path):
    ctx = create_run(root, run_id="youtube-run")
    package_dir = ctx.path("package/youtube")
    package_dir.mkdir(parents=True, exist_ok=True)
    for name in ["video.mp4", "title.txt", "description.md", "tags.txt"]:
        (package_dir / name).write_text("ok", encoding="utf-8")
    write_yaml(
        package_dir / "metadata_qa.yml",
        {
            "status": "passed",
            "checks": {
                "video_exists": True,
                "thumbnail_exists": True,
                "thumbnail_size_1280x720": True,
                "title_exists": True,
                "title_length_ok": True,
                "description_exists": True,
                "chapters_start_at_zero": True,
                "tags_exists": True,
                "tags_count_ok": True,
                "upload_gate_pending": True,
                "publish_gate_pending": True,
            },
        },
    )
    return ctx


if __name__ == "__main__":
    unittest.main()
