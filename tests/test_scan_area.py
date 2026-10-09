import unittest

import cv2
import numpy as np

from smart_scan.scan_area import ScanArea, selected_area


class ScanAreaTests(unittest.TestCase):
    def test_full_height_orange_selection(self):
        frame = np.zeros((660, 880, 3), dtype=np.uint8)
        frame[:, 0] = (15, 132, 237)
        frame[:, 352] = (15, 132, 237)
        frame[0, :353] = (15, 132, 237)
        frame[-1, :353] = (15, 132, 237)
        self.assertEqual(selected_area(frame),
                         ScanArea(((0, 0), (352, 0), (352, 659), (0, 659))))

    def test_no_selection_does_not_enable_auto_scan(self):
        frame = np.zeros((660, 880, 3), dtype=np.uint8)
        frame[:, 0] = (15, 132, 237)
        self.assertIsNone(selected_area(frame))

    def test_dim_orange_selection_is_detected(self):
        frame = np.zeros((660, 880, 3), dtype=np.uint8)
        cv2.rectangle(frame, (25, 20), (855, 639), (0, 57, 134), 2)
        area = selected_area(frame)
        self.assertIsNotNone(area)
        expected = np.array(((25, 20), (855, 20), (855, 639), (25, 639)))
        self.assertLessEqual(np.max(np.abs(np.asarray(area.corners) - expected)), 2)

    def test_orange_object_without_border_is_not_a_scan_area(self):
        frame = np.zeros((660, 880, 3), dtype=np.uint8)
        cv2.rectangle(frame, (300, 220), (500, 440), (0, 57, 134), -1)
        self.assertIsNone(selected_area(frame))

    def test_full_camera_selection(self):
        frame = np.zeros((660, 880, 3), dtype=np.uint8)
        frame[:, 0] = (15, 132, 237)
        frame[:, -1] = (15, 132, 237)
        frame[0] = (15, 132, 237)
        frame[-1] = (15, 132, 237)
        self.assertEqual(selected_area(frame),
                         ScanArea(((0, 0), (879, 0), (879, 659), (0, 659))))

    def test_slanted_selection_is_rectified(self):
        frame = np.zeros((527, 702, 3), dtype=np.uint8)
        corners = np.array([[222, 1], [497, 20], [465, 496], [190, 479]], np.int32)
        cv2.polylines(frame, [corners], True, (15, 132, 237), 1)
        area = selected_area(frame)
        self.assertIsNotNone(area)
        self.assertLessEqual(np.max(np.abs(np.asarray(area.corners) - corners)), 2)
        self.assertGreater(area.extract(frame).shape[0], 450)

    def test_broken_border_ignores_isolated_orange_mark(self):
        frame = np.zeros((660, 880, 3), dtype=np.uint8)
        color = (0, 57, 134)
        for y in range(10, 631, 75):
            cv2.line(frame, (20, y), (20, min(y + 52, 630)), color, 1)
            cv2.line(frame, (790, y), (790, min(y + 52, 630)), color, 1)
        for x in range(20, 791, 75):
            cv2.line(frame, (x, 10), (min(x + 52, 790), 10), color, 1)
            cv2.line(frame, (x, 630), (min(x + 52, 790), 630), color, 1)
        cv2.circle(frame, (840, 605), 8, color, -1)
        area = selected_area(frame)
        self.assertIsNotNone(area)
        expected = np.array(((20, 10), (790, 10), (790, 630), (20, 630)))
        self.assertLessEqual(np.max(np.abs(np.asarray(area.corners) - expected)), 3)

    def test_selection_using_camera_edges(self):
        frame = np.zeros((267, 355, 3), dtype=np.uint8)
        frame[:, 97] = (15, 132, 237)
        frame[-1, :98] = (15, 132, 237)
        self.assertEqual(selected_area(frame),
                         ScanArea(((0, 0), (97, 0), (97, 266), (0, 266))))


if __name__ == "__main__":
    unittest.main()
