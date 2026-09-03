"""Focused regression tests for safety and argument-handling helpers."""

import contextlib
import importlib.machinery
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
# spec_from_loader + module_from_spec is the forward-safe replacement for
# SourceFileLoader(...).load_module(), which still works on 3.12/3.13 but
# emits a DeprecationWarning.
_spec = importlib.util.spec_from_loader(
    "atlas_desktop_test",
    importlib.machinery.SourceFileLoader("atlas_desktop_test", str(ROOT / "desktop")),
)
desktop = importlib.util.module_from_spec(_spec)
sys.modules["atlas_desktop_test"] = desktop
_spec.loader.exec_module(desktop)


class DesktopSafetyTests(unittest.TestCase):
    def test_real_click_refuses_point_outside_target_window(self):
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(
                desktop, "_arc_window_geometry",
                lambda browser: {"x": 100, "y": 100, "w": 400, "h": 300}))
            stack.enter_context(mock.patch.object(
                desktop, "_dom_window_metrics",
                lambda browser: {"dpr": 1, "innerW": 400, "innerH": 300}))
            stack.enter_context(mock.patch.object(
                desktop, "_check_js_geometry_against_ax",
                lambda metrics, frame: (True, {})))
            stack.enter_context(mock.patch.object(
                desktop, "resolve_window_display",
                lambda browser: {
                    "originXQuartz": 0, "originYQuartz": 0,
                    "widthPoints": 1920, "heightPoints": 1080, "screenIndex": 0,
                }))
            stack.enter_context(mock.patch.object(
                desktop, "get_top_chrome", lambda *args: (0, True, "test", False)))
            stack.enter_context(mock.patch.object(
                desktop, "get_left_chrome", lambda *args: (0, True, "test", False)))
            stack.enter_context(mock.patch.object(
                desktop, "_screen_backing_scale_factor", lambda frame: (1, True, 0)))
            stack.enter_context(mock.patch.object(
                desktop, "_viewport_to_screen", lambda *args: (600, 200)))
            stack.enter_context(mock.patch.object(
                desktop, "run_jxa_ax", lambda *args, **kwargs: {"ok": True}))
            clicks = []
            stack.enter_context(mock.patch.object(
                desktop, "cliclick", lambda arg: clicks.append(arg) or {"ok": True}))

            result = desktop.real_click_verified(
                "Arc", {"vx": 0, "vy": 0, "vw": 1, "vh": 1},
                lambda: (False, None, None),
            )

        self.assertEqual("point-out-of-bounds", result["reason"])
        self.assertEqual([], clicks)

    def test_real_click_allows_point_in_window_despite_display_mismatch(self):
        # Regression for the too-strict bounds check: a point inside the
        # target window must still be clicked even when resolve_window_display
        # picked the wrong display (e.g. a hardware-mirrored display), with
        # the mismatch surfaced only as a warning, not a refusal.
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(
                desktop, "_arc_window_geometry",
                lambda browser: {"x": 100, "y": 100, "w": 400, "h": 300}))
            stack.enter_context(mock.patch.object(
                desktop, "_dom_window_metrics",
                lambda browser: {"dpr": 1, "innerW": 400, "innerH": 300}))
            stack.enter_context(mock.patch.object(
                desktop, "_check_js_geometry_against_ax",
                lambda metrics, frame: (True, {})))
            # Resolved display is nowhere near the target window (100,100)-
            # (500,400), so a click inside the window falls outside this
            # display frame -- the mismatch case.
            stack.enter_context(mock.patch.object(
                desktop, "resolve_window_display",
                lambda browser: {
                    "originXQuartz": 5000, "originYQuartz": 5000,
                    "widthPoints": 1920, "heightPoints": 1080, "screenIndex": 1,
                }))
            stack.enter_context(mock.patch.object(
                desktop, "get_top_chrome", lambda *args: (0, True, "test", False)))
            stack.enter_context(mock.patch.object(
                desktop, "get_left_chrome", lambda *args: (0, True, "test", False)))
            stack.enter_context(mock.patch.object(
                desktop, "_screen_backing_scale_factor", lambda frame: (1, True, 0)))
            # Center of the window, well inside (100,100)-(500,400).
            stack.enter_context(mock.patch.object(
                desktop, "_viewport_to_screen", lambda *args: (300, 250)))
            stack.enter_context(mock.patch.object(
                desktop, "run_jxa_ax", lambda *args, **kwargs: {"ok": True}))
            clicks = []
            stack.enter_context(mock.patch.object(
                desktop, "cliclick", lambda arg: clicks.append(arg) or {"ok": True}))

            result = desktop.real_click_verified(
                "Arc", {"vx": 0, "vy": 0, "vw": 1, "vh": 1},
                lambda: (True, "test", None),
            )

        self.assertNotEqual("point-out-of-bounds", result["reason"])
        self.assertEqual(["c:300,250"], clicks)
        self.assertIn("displayMismatchWarning", result["jsGeometryCheck"])

    def test_find_one_rejects_negative_index(self):
        with mock.patch.object(
                desktop, "run_jxa_ax",
                lambda *args, **kwargs: {"matches": ["first", "last"]}):
            element, error = desktop.find_one("button", None, -1, None)

        self.assertIsNone(element)
        self.assertIn("no match at index -1", error["error"])

    def test_osascript_browser_name_is_escaped(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

        with mock.patch.object(desktop.subprocess, "run", fake_run):
            desktop._arc_execute_js("1 + 1", 'Arc" malicious')

        self.assertIn('tell application "Arc\\" malicious"', calls[0][2])

    def test_subprocess_run_is_not_contaminated_after_escaping_test(self):
        # Proves the patch above was scoped and torn down: desktop.subprocess
        # is the shared subprocess module object, so an unscoped assignment
        # in the prior test would leak a stub into every later test (and
        # into real callers) instead of being restored.
        result = desktop.subprocess.run(
            ["echo", "hello"], capture_output=True, text=True
        )
        self.assertEqual("hello\n", result.stdout)


if __name__ == "__main__":
    unittest.main()
