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
        args = parser.parse_args(["approve", "--run", "runs/demo", "--gate", "plan"])
        self.assertEqual(args.run, "runs/demo")
        self.assertEqual(args.gate, "plan")


if __name__ == "__main__":
    unittest.main()
