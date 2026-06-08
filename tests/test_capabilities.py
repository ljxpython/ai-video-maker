import unittest

from ai_video_maker.capabilities import capability_plan_from_pipeline, required_capability_names


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


if __name__ == "__main__":
    unittest.main()
