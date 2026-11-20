import unittest

from observer_app.desktop import russian_timeline
from observer_app.server import ObserverApplication


class DesktopViewTests(unittest.TestCase):
    def test_fixture_timeline_is_shown_in_russian(self) -> None:
        titles = [title for title, _ in russian_timeline(ObserverApplication().snapshot())]
        self.assertIn("Корневой turn завершён", titles)
        self.assertIn("Уточнение завершено", titles)

    def test_preview_event_remains_visible_without_runtime_claim(self) -> None:
        application = ObserverApplication()
        application.action("interrupt")
        titles = [title for title, _ in russian_timeline(application.snapshot())]
        self.assertIn("Прерывание запрошено в демо-режиме", titles)


if __name__ == "__main__":
    unittest.main()
