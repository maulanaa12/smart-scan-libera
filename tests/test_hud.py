import unittest

import numpy as np

from smart_scan import core
from smart_scan.scan_area import ScanArea

from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path


class HudTests(unittest.TestCase):
    def test_status_bars_do_not_cover_camera_pixels(self):
        source = np.zeros((600, 800, 3), dtype=np.uint8)
        source[0, 0] = (5, 50, 120)
        source[-1, -1] = (30, 150, 230)
        spec = spec_from_file_location("smart_scan_entry", Path(__file__).resolve().parents[1] / "smart_scan.py")
        entry = module_from_spec(spec)
        spec.loader.exec_module(entry)
        observation = core.Observation(0, 0, core.HandStatus.CLEAR)
        decision = core.Decision(core.State.IDLE)
        hud = entry.draw_hud(source, decision, observation, 0, [], True, 800, 600)
        self.assertEqual(hud.shape, (714, 800, 3))
        np.testing.assert_array_equal(hud[72, 0], source[0, 0])
        np.testing.assert_array_equal(hud[671, 799], source[-1, -1])

    def test_analysis_mark_is_inside_full_preview(self):
        source = np.zeros((600, 800, 3), dtype=np.uint8)
        spec = spec_from_file_location("smart_scan_entry", Path(__file__).resolve().parents[1] / "smart_scan.py")
        entry = module_from_spec(spec)
        spec.loader.exec_module(entry)
        observation = core.Observation(0, 0, core.HandStatus.CLEAR)
        decision = core.Decision(core.State.IDLE)
        hud = entry.draw_hud(source, decision, observation, 0, [], True, 800, 600,
                             ScanArea(((0, 0), (320, 0), (320, 599), (0, 599))))
        np.testing.assert_array_equal(hud[300, 320], [0, 220, 255])
        np.testing.assert_array_equal(hud[300, 600], [0, 0, 0])


if __name__ == "__main__":
    unittest.main()
