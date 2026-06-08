import unittest

from ai_video_maker.capabilities import browser_preflight_plan_from_pipeline, capability_plan_from_pipeline, required_capability_names


class CapabilityTests(unittest.TestCase):
    def test_capability_plan_marks_optional_tools(self):
        plan = capability_plan_from_pipeline({"capabilities": {}})

        self.assertEqual(plan["mode"], "dry_run")
        self.assertEqual(plan["required"], [])
        self.assertEqual({item["name"] for item in plan["capabilities"]}, {"browser", "chrome", "computer_use"})
        self.assertTrue(all(item["action"] == "dry_run_only" for item in plan["capabilities"]))

    def test_capability_plan_marks_required_tools(self):
        pipeline = {
            "capabilities": {
                "browser": {"required": True},
                "chrome": {"required": False},
                "computer_use": {"required": True},
            }
        }

        plan = capability_plan_from_pipeline(pipeline)

        self.assertEqual(plan["required"], ["browser", "computer_use"])
        self.assertEqual(required_capability_names(pipeline), ["browser", "computer_use"])
        statuses = {item["name"]: item["status"] for item in plan["capabilities"]}
        self.assertEqual(statuses["browser"], "requires_execution_approval")
        self.assertEqual(statuses["chrome"], "optional")
        self.assertEqual(statuses["computer_use"], "requires_execution_approval")

    def test_browser_preflight_plan_for_local_demo(self):
        pipeline = {
            "capabilities": {
                "browser": {
                    "required": True,
                    "target_url": "http://localhost:8000",
                    "viewport": {"width": 1920, "height": 1080},
                    "checks": ["page_load", "screenshot_non_blank"],
                    "recording": {
                        "enabled": True,
                        "duration_seconds": 12,
                        "output": "assets/browser/demo.mp4",
                    },
                }
            }
        }

        preflight = browser_preflight_plan_from_pipeline(pipeline)

        self.assertTrue(preflight["enabled"])
        self.assertTrue(preflight["required"])
        self.assertEqual(preflight["status"], "ready_for_execution_gate")
        self.assertEqual(preflight["target_kind"], "local_web")
        self.assertEqual(preflight["viewport"], {"width": 1920, "height": 1080})
        self.assertEqual(preflight["recording"]["duration_seconds"], 12)
        self.assertEqual(preflight["recording"]["output"], "assets/browser/demo.mp4")

    def test_browser_preflight_handles_missing_target_url(self):
        preflight = browser_preflight_plan_from_pipeline({"capabilities": {"browser": {"required": True}}})

        self.assertTrue(preflight["enabled"])
        self.assertEqual(preflight["status"], "missing_target_url")
        self.assertEqual(preflight["target_kind"], "none")


if __name__ == "__main__":
    unittest.main()
