import unittest

import cv2
import numpy as np

from smart_scan.finger_edges import box_allowed, edge_skin_boxes


ZONES = [[0, 0.82, 1, 1], [0, 0, 0.13, 0.18]]


class FingerEdgeTests(unittest.TestCase):
    def test_bottom_finger_is_allowed_but_center_finger_is_not(self):
        frame = np.full((200, 300, 3), 255, dtype=np.uint8)
        cv2.rectangle(frame, (120, 175), (135, 199), (80, 125, 180), -1)
        boxes = edge_skin_boxes(frame, 0.03)
        self.assertEqual(len(boxes), 1)
        self.assertTrue(box_allowed(boxes[0], ZONES))
        cv2.rectangle(frame, (120, 90), (135, 199), (80, 125, 180), -1)
        boxes = edge_skin_boxes(frame, 0.03)
        self.assertEqual(len(boxes), 1)
        self.assertFalse(box_allowed(boxes[0], ZONES))

    def test_skin_colored_photo_inside_page_is_not_edge_finger(self):
        frame = np.full((200, 300, 3), 255, dtype=np.uint8)
        cv2.rectangle(frame, (110, 60), (170, 120), (80, 125, 180), -1)
        self.assertEqual(edge_skin_boxes(frame, 0.03), [])

    def test_red_sheet_is_not_a_hand_but_finger_still_blocks(self):
        frame = np.full((200, 300, 3), 255, dtype=np.uint8)
        cv2.rectangle(frame, (0, 0), (149, 164), (95, 103, 180), -1)
        self.assertEqual(edge_skin_boxes(frame, 0.03), [])
        cv2.rectangle(frame, (220, 105), (235, 199), (80, 125, 180), -1)
        boxes = edge_skin_boxes(frame, 0.03)
        self.assertEqual(len(boxes), 1)
        self.assertFalse(box_allowed(boxes[0], ZONES))


if __name__ == "__main__":
    unittest.main()
