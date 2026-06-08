import tempfile
import unittest
from pathlib import Path

from ai_video_maker.context import create_run
from ai_video_maker.io import read_yaml, write_yaml
from ai_video_maker.publish_package_workflow import generate_publish_package


class PublishPackageWorkflowTests(unittest.TestCase):
    def test_generate_publish_package_requires_qa_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_run(Path(tmp), run_id="package-run")

            with self.assertRaises(FileNotFoundError):
                generate_publish_package(ctx)

    def test_generate_publish_package_writes_files_and_keeps_gates_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_publish_run(Path(tmp))

            handoff = generate_publish_package(ctx)

            self.assertEqual(handoff["skill"], "publish-package")
            self.assertEqual(handoff["status"], "ready_for_gate")
            self.assertEqual(handoff["next_gate"], "upload")
            self.assertTrue(ctx.path("package/video.mp4").exists())
            self.assertTrue(ctx.path("package/title.txt").exists())
            self.assertTrue(ctx.path("package/description.md").exists())
            self.assertTrue(ctx.path("package/tags.txt").exists())
            self.assertTrue(ctx.path("package/upload_checklist.md").exists())
            self.assertEqual(read_yaml(ctx.path("package/handoff.publish-package.yml"))["skill"], "publish-package")
            approvals = read_yaml(ctx.approvals_path)
            self.assertEqual(approvals["upload"]["status"], "pending")
            self.assertEqual(approvals["publish"]["status"], "pending")
            self.assertEqual(ctx.state()["status"], "publish_package_ready")

    def test_generate_publish_package_rejects_failed_qa(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = create_publish_run(Path(tmp))
            write_yaml(ctx.path("qa/handoff.qa-revision.yml"), {"skill": "qa-revision", "status": "needs_revision"})

            with self.assertRaises(PermissionError):
                generate_publish_package(ctx)


def create_publish_run(root: Path):
    ctx = create_run(root, run_id="package-run")
    write_yaml(ctx.path("qa/handoff.qa-revision.yml"), {"skill": "qa-revision", "status": "ready_for_review"})
    ctx.path("render/final_16x9.mp4").write_bytes(b"video")
    write_yaml(
        ctx.path("pipeline.yml"),
        {
            "project": {"name": "Demo Project", "type": "general_demo"},
            "source": {"type": "user_request", "value": "介绍 Demo Project"},
            "video": {"style": "横屏技术讲解"},
        },
    )
    return ctx


if __name__ == "__main__":
    unittest.main()
