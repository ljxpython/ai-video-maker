import unittest

from ai_video_maker.browser_actions import normalize_screen_actions


class BrowserActionsTests(unittest.TestCase):
    def test_normalize_screen_actions_fills_defaults(self):
        plan = normalize_screen_actions(
            {
                "version": 1,
                "target_url": "http://localhost:8000",
                "actions": [{"id": "open", "type": "goto", "url": "http://localhost:8000"}],
            }
        )

        self.assertEqual(plan["viewport"]["width"], 1920)
        self.assertTrue(plan["recording"]["enabled"])

    def test_duplicate_action_id_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_screen_actions(
                {
                    "version": 1,
                    "target_url": "http://localhost:8000",
                    "actions": [
                        {"id": "open", "type": "goto", "url": "http://localhost:8000"},
                        {"id": "open", "type": "wait"},
                    ],
                }
            )

    def test_click_requires_selector(self):
        with self.assertRaises(ValueError):
            normalize_screen_actions({"version": 1, "target_url": "http://localhost:8000", "actions": [{"id": "click", "type": "click"}]})


if __name__ == "__main__":
    unittest.main()
