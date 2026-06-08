import tempfile
import unittest
from pathlib import Path

from ai_video_maker.srt import active_caption, parse_srt, parse_time


class SrtTests(unittest.TestCase):
    def test_parse_time(self):
        self.assertEqual(parse_time("00:00:01,500"), 1.5)
        self.assertEqual(parse_time("01:02:03,004"), 3723.004)

    def test_parse_srt_and_active_caption(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "captions.srt"
            path.write_text(
                "\n".join(
                    [
                        "1",
                        "00:00:00,100 --> 00:00:01,500",
                        "第一句",
                        "",
                        "2",
                        "00:00:02,000 --> 00:00:03,000",
                        "第二句",
                        "跨行",
                    ]
                ),
                encoding="utf-8",
            )

            captions = parse_srt(path)

        self.assertEqual(captions, [(0.1, 1.5, "第一句"), (2.0, 3.0, "第二句 跨行")])
        self.assertEqual(active_caption(captions, 0.2), "第一句")
        self.assertEqual(active_caption(captions, 2.5), "第二句 跨行")
        self.assertEqual(active_caption(captions, 1.8), "")

    def test_parse_empty_srt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.srt"
            path.write_text("", encoding="utf-8")
            self.assertEqual(parse_srt(path), [])


if __name__ == "__main__":
    unittest.main()
