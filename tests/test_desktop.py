"""Focused regression tests for safety and argument-handling helpers."""

import importlib.machinery
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
desktop = importlib.machinery.SourceFileLoader(
    "atlas_desktop_test", str(ROOT / "desktop")
).load_module()


class DesktopSafetyTests(unittest.TestCase):
    def test_real_click_refuses_point_outside_target_window(self):
        desktop._arc_window_geometry = lambda browser: {
            "x": 100, "y": 100, "w": 400, "h": 300,
        }
        desktop._dom_window_metrics = lambda browser: {
            "dpr": 1, "innerW": 400, "innerH": 300,
        }
        desktop._check_js_geometry_against_ax = lambda metrics, frame: (True, {})
        desktop.resolve_window_display = lambda browser: {
            "originXQuartz": 0, "originYQuartz": 0,
            "widthPoints": 1920, "heightPoints": 1080, "screenIndex": 0,
        }
        desktop.get_top_chrome = lambda *args: (0, True, "test", False)
        desktop.get_left_chrome = lambda *args: (0, True, "test", False)
        desktop._screen_backing_scale_factor = lambda frame: (1, True, 0)
        desktop._viewport_to_screen = lambda *args: (600, 200)
        desktop.run_jxa_ax = lambda *args, **kwargs: {"ok": True}
        clicks = []
        desktop.cliclick = lambda arg: clicks.append(arg) or {"ok": True}

        result = desktop.real_click_verified(
            "Arc", {"vx": 0, "vy": 0, "vw": 1, "vh": 1},
            lambda: (False, None, None),
        )

        self.assertEqual("point-out-of-bounds", result["reason"])
        self.assertEqual([], clicks)

    def test_find_one_rejects_negative_index(self):
        desktop.run_jxa_ax = lambda *args, **kwargs: {"matches": ["first", "last"]}

        element, error = desktop.find_one("button", None, -1, None)

        self.assertIsNone(element)
        self.assertIn("no match at index -1", error["error"])

    def test_osascript_browser_name_is_escaped(self):
        calls = []
        desktop.subprocess.run = lambda command, **kwargs: calls.append(command) or type(
            "Result", (), {"returncode": 0, "stdout": "", "stderr": ""}
        )()

        desktop._arc_execute_js("1 + 1", 'Arc" malicious')

        self.assertIn('tell application "Arc\\" malicious"', calls[0][2])


if __name__ == "__main__":
    unittest.main()
