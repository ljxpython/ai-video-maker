import unittest

from ai_video_maker.cli import build_parser


class CliTests(unittest.TestCase):
    def test_parser_accepts_run_demo(self):
        parser = build_parser()
        args = parser.parse_args(["run-demo", "--run-id", "demo", "--overwrite"])
        self.assertEqual(args.run_id, "demo")
        self.assertTrue(args.overwrite)

    def test_parser_accepts_approval_gate(self):
        parser = build_parser()
        args = parser.parse_args(["approve", "--run", "runs/demo", "--gate", "plan", "--summary", "ok"])
        self.assertEqual(args.run, "runs/demo")
        self.assertEqual(args.gate, "plan")
        self.assertEqual(args.summary, "ok")

    def test_parser_accepts_pipeline_run(self):
        parser = build_parser()
        args = parser.parse_args(["run", "--pipeline", "pipeline.example.yml", "--run-id", "demo", "--overwrite"])
        self.assertEqual(args.pipeline, "pipeline.example.yml")
        self.assertEqual(args.run_id, "demo")
        self.assertTrue(args.overwrite)

    def test_parser_accepts_status(self):
        parser = build_parser()
        args = parser.parse_args(["status", "--run", "runs/demo", "--json"])
        self.assertEqual(args.run, "runs/demo")
        self.assertTrue(args.json)

    def test_parser_accepts_validate(self):
        parser = build_parser()
        args = parser.parse_args(["validate", "--pipeline", "pipeline.example.yml", "--json"])
        self.assertEqual(args.pipeline, "pipeline.example.yml")
        self.assertTrue(args.json)


if __name__ == "__main__":
    unittest.main()
