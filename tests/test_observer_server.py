import unittest

from observer_app.server import ObserverApplication, PreviewState


class ObserverServerTests(unittest.TestCase):
    def test_projection_is_fixture_backed(self) -> None:
        snapshot = ObserverApplication().snapshot()
        self.assertEqual(snapshot["projection"]["fixture"], "live-controls-normalized.json")
        self.assertEqual(snapshot["preview"]["lifecycle"], "Open")

    def test_preview_actions_do_not_create_runtime_turn_data(self) -> None:
        application = ObserverApplication()
        snapshot = application.action("follow-up")
        self.assertEqual(snapshot["preview"]["events"][0]["title"], "Follow-up staged locally")
        self.assertNotIn("turnId", snapshot["preview"]["events"][0])

    def test_finish_is_local_lifecycle_only(self) -> None:
        application = ObserverApplication()
        snapshot = application.action("finish")
        self.assertEqual(snapshot["preview"]["lifecycle"], "Finished")
        self.assertTrue(snapshot["projection"]["outcome"]["success"])

    def test_unknown_preview_action_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PreviewState().apply("approve")


if __name__ == "__main__":
    unittest.main()
