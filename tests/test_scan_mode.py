import unittest

import cv2
import numpy as np

from smart_scan.scan_area import ScanArea, full_frame_area, selected_area
from smart_scan.scan_mode import ScanMode, detect_scan_mode


class ScanModeTests(unittest.TestCase):
    def setUp(self):
        self.frame = np.full((900, 1100, 3), (50, 50, 50), dtype=np.uint8)
        self.camera_rect = (0, 150, 760, 750)

    def radios(self, selected_index):
        for index in range(5):
            color = ((14, 156, 245) if index == selected_index else
                     (250, 250, 250))
            cv2.circle(self.frame, (870, 470 + index * 63), 7, color, -1)

    def test_original_image_uses_the_whole_camera_without_orange_border(self):
        self.radios(4)
        camera = self.frame[150:750, :760]
        self.assertEqual(detect_scan_mode(self.frame, self.camera_rect),
                         ScanMode.ORIGINAL_IMAGE)
        self.assertIsNone(selected_area(camera))
        self.assertEqual(full_frame_area(camera),
                         ScanArea(((0, 0), (759, 0), (759, 599), (0, 599))))

    def test_document_mode_does_not_use_full_camera(self):
        self.radios(0)
        self.assertEqual(detect_scan_mode(self.frame, self.camera_rect),
                         ScanMode.DOCUMENT)

    def test_document_still_detected_when_another_radio_is_dimmed(self):
        self.radios(0)
        cv2.circle(self.frame, (870, 470 + 4 * 63), 7, (160, 135, 109), -1)
        self.assertEqual(detect_scan_mode(self.frame, self.camera_rect),
                         ScanMode.DOCUMENT)

    def test_other_mode_is_not_mistaken_for_original(self):
        self.radios(2)
        self.assertEqual(detect_scan_mode(self.frame, self.camera_rect),
                         ScanMode.SELECT_AREA)

    def test_single_orange_dot_cannot_enable_full_camera(self):
        cv2.circle(self.frame, (870, 722), 7, (14, 156, 245), -1)
        self.assertIsNone(detect_scan_mode(self.frame, self.camera_rect))


if __name__ == "__main__":
    unittest.main()
