import unittest

import cv2
import numpy as np

from smart_scan.scan_area import ScanArea, area_for_mode
from smart_scan.scan_mode import ScanMode


class ModeAreaTests(unittest.TestCase):
    def setUp(self):
        self.frame = np.full((660, 880, 3), (50, 100, 40), dtype=np.uint8)

    def test_book_spine_guide_does_not_crop_out_a_page(self):
        cv2.rectangle(self.frame, (410, 0), (470, 659), (30, 110, 160), -1)
        cv2.line(self.frame, (440, 0), (440, 659), (15, 132, 237), 2)
        self.assertEqual(area_for_mode(self.frame, ScanMode.BOOK),
                         ScanArea(((0, 0), (879, 0), (879, 659), (0, 659))))

    def test_select_area_uses_small_red_rectangle_and_excludes_instruction(self):
        cv2.putText(self.frame, "Please manually select the scanning area", (50, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.rectangle(self.frame, (130, 180), (600, 460), (0, 0, 255), 1)
        area = area_for_mode(self.frame, ScanMode.SELECT_AREA)
        self.assertEqual(area, ScanArea(((130, 180), (600, 180), (600, 460), (130, 460))))
        self.assertIsNone(area_for_mode(self.frame, ScanMode.DOCUMENT))

    def test_selected_area_survives_resizing(self):
        cv2.rectangle(self.frame, (130, 180), (600, 460), (0, 0, 255), 1)
        resized = cv2.resize(self.frame, (1000, 750))
        area = area_for_mode(resized, ScanMode.SELECT_AREA)
        self.assertIsNotNone(area)
        expected = np.array(((130, 180), (600, 180), (600, 460), (130, 460))) * (1000 / 880)
        self.assertLessEqual(np.max(np.abs(np.array(area.corners) - expected)), 2)

    def test_no_rectangle_keeps_auto_scan_disabled(self):
        self.assertIsNone(area_for_mode(self.frame, ScanMode.SELECT_AREA))
        cv2.line(self.frame, (130, 180), (600, 180), (0, 0, 255), 1)
        cv2.line(self.frame, (130, 180), (130, 460), (0, 0, 255), 1)
        self.assertIsNone(area_for_mode(self.frame, ScanMode.SELECT_AREA))

    def test_red_divider_is_not_a_manual_selection(self):
        cv2.rectangle(self.frame, (130, 180), (600, 460), (0, 0, 255), -1)
        self.assertIsNone(area_for_mode(self.frame, ScanMode.SELECT_AREA))

    def test_mouse_held_does_not_enable_scan_even_with_complete_rectangle(self):
        cv2.rectangle(self.frame, (130, 180), (600, 460), (0, 0, 255), 1)
        self.assertIsNone(area_for_mode(self.frame, ScanMode.SELECT_AREA, selecting=True))
        self.assertIsNotNone(area_for_mode(self.frame, ScanMode.SELECT_AREA, selecting=False))

    def test_unknown_mode_does_not_reuse_book_or_manual_selection(self):
        for previous in (ScanMode.BOOK, ScanMode.SELECT_AREA, ScanMode.ORIGINAL_IMAGE):
            self.assertIsNone(area_for_mode(self.frame, None, previous))


if __name__ == "__main__":
    unittest.main()
