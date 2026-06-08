import unittest
from pathlib import Path

from ai_video_maker.skill_distribution import validate_skills


class SkillDistributionTests(unittest.TestCase):
    def test_validate_repository_skills(self):
        root = Path(__file__).resolve().parents[1]

        result = validate_skills(root)

        self.assertEqual(result["status"], "passed", result["errors"])
        self.assertGreaterEqual(result["count"], 10)


if __name__ == "__main__":
    unittest.main()
