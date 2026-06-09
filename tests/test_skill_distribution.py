import unittest
from pathlib import Path

from ai_video_maker.skill_distribution import validate_skills


class SkillDistributionTests(unittest.TestCase):
    def test_agents_skills_entry_exists(self):
        root = Path(__file__).resolve().parents[1]
        entry = root / ".agents" / "skills"

        self.assertTrue(entry.exists(), ".agents/skills entry is missing")
        self.assertEqual(entry.resolve(), (root / "skills").resolve())

    def test_validate_repository_skills(self):
        root = Path(__file__).resolve().parents[1]

        result = validate_skills(root)

        self.assertEqual(result["status"], "passed", result["errors"])
        self.assertGreaterEqual(result["count"], 10)


if __name__ == "__main__":
    unittest.main()
