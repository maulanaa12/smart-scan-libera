import unittest

import numpy as np

from smart_scan.viewport import find_camera_rect, validate_layout


LAYOUT = {
    "sidebar_width_px": 180,
    "controls_width_px": 260,
    "toolbar_height_px": 70,
    "camera_aspect_ratio": 4 / 3,
}


def window_with_camera(size, rect):
    width, height = size
    frame = np.full((height, width, 3), (62, 55, 51), dtype=np.uint8)
    x1, y1, x2, y2 = rect
    frame[y1:y2, x1:x2] = (20, 90, 120)
    return frame


class ViewportTests(unittest.TestCase):
    def test_camera_fits_narrow_libera_window(self):
        rect = (180, 145, 1060, 805)
        self.assertEqual(find_camera_rect(window_with_camera((1320, 880), rect), LAYOUT), rect)

    def test_camera_fits_maximized_libera_window(self):
        rect = (247, 70, 1593, 1080)
        self.assertEqual(find_camera_rect(window_with_camera((1920, 1080), rect), LAYOUT), rect)

    def test_shrunk_preview_is_found_by_pixels(self):
        rect = (340, 310, 740, 610)
        self.assertEqual(find_camera_rect(window_with_camera((1320, 880), rect), LAYOUT), rect)

    def test_darker_controls_panel_does_not_hide_camera(self):
        rect = (180, 145, 1060, 805)
        frame = window_with_camera((1320, 880), rect)
        frame[145:805, 180:1060] = (2, 2, 3)
        frame[:, 1060:] = (49, 44, 40)
        self.assertEqual(find_camera_rect(frame, LAYOUT), rect)

    def test_restored_window_with_shifted_sidebar_and_panel(self):
        rect = (169, 150, 1049, 810)
        frame = np.full((885, 1920, 3), (62, 55, 51), dtype=np.uint8)
        frame[75:, :169] = (255, 255, 255)
        frame[75:, 1049:] = (49, 44, 40)
        frame[150:810, 169:1049] = (2, 2, 3)
        self.assertEqual(find_camera_rect(frame, LAYOUT), rect)

    def test_missing_preview_is_rejected(self):
        frame = np.full((880, 1320, 3), (62, 55, 51), dtype=np.uint8)
        self.assertIsNone(find_camera_rect(frame, LAYOUT))

    def test_invalid_layout_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_layout({**LAYOUT, "camera_aspect_ratio": 0})


if __name__ == "__main__":
    unittest.main()
