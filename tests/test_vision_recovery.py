import unittest
from types import SimpleNamespace

import numpy as np

from smart_scan.core import HandStatus
from smart_scan.scan_area import ScanArea
from smart_scan.vision import VisionAnalyzer


class VisionRecoveryTests(unittest.TestCase):
    def make_vision(self):
        vision = VisionAnalyzer.__new__(VisionAnalyzer)
        vision.camera = SimpleNamespace(update=lambda frame, now: True)
        vision.pixel_delta = 25
        vision.prev_gray = None
        vision.reference_gray = None
        vision.last_mask = None
        vision.reference_mask = None
        vision.frame_size = None
        vision.zones = []
        vision._hand_status = lambda frame, now: HandStatus.CLEAR
        return vision

    def test_short_area_loss_keeps_scene_reference_without_inventing_motion(self):
        vision = self.make_vision()
        area = ScanArea(((20, 20), (380, 20), (380, 280), (20, 280)))
        old_page = np.full((300, 400, 3), 50, dtype=np.uint8)
        new_page = np.full((300, 400, 3), 200, dtype=np.uint8)

        self.assertEqual(vision.analyze(old_page, 0, area).scene_change_percent, 0)
        self.assertFalse(vision.analyze(old_page, 0.1, None).area_valid)
        recovered = vision.analyze(new_page, 0.2, area)

        self.assertEqual(recovered.motion_percent, 0)
        self.assertGreater(recovered.scene_change_percent, 90)

    def test_selection_border_shift_does_not_erase_page_change(self):
        vision = self.make_vision()
        first_area = ScanArea(((20, 20), (380, 20), (380, 280), (20, 280)))
        shifted_area = ScanArea(((35, 20), (395, 20), (395, 280), (35, 280)))
        page = np.full((300, 400, 3), 80, dtype=np.uint8)
        page[70:230, 100:300] = 160

        vision.analyze(page, 0, first_area)
        self.assertEqual(vision.analyze(page, 0.1, shifted_area).scene_change_percent, 0)

        changed_page = page.copy()
        changed_page[70:230, 100:300] = 30
        observation = vision.analyze(changed_page, 0.2, shifted_area)
        self.assertGreater(observation.scene_change_percent, 15)

    def test_allowed_hand_zone_does_not_count_as_new_page(self):
        vision = self.make_vision()
        vision.zones = [[0.0, 0.82, 1.0, 1.0]]
        area = ScanArea(((20, 20), (380, 20), (380, 280), (20, 280)))
        page = np.full((300, 400, 3), 80, dtype=np.uint8)
        vision.analyze(page, 0, area)

        finger_at_bottom = page.copy()
        finger_at_bottom[250:275, 80:320] = 220
        self.assertLess(vision.analyze(finger_at_bottom, 0.1, area).scene_change_percent, 3)

        changed_page = finger_at_bottom.copy()
        changed_page[75:180, 90:310] = 220
        self.assertGreater(vision.analyze(changed_page, 0.2, area).scene_change_percent, 10)

    def test_camera_size_change_resets_scene_reference(self):
        vision = self.make_vision()
        area = ScanArea(((20, 20), (380, 20), (380, 280), (20, 280)))
        vision.analyze(np.full((300, 400, 3), 60, dtype=np.uint8), 0, area)
        larger_area = ScanArea(((20, 20), (480, 20), (480, 380), (20, 380)))
        observation = vision.analyze(np.full((400, 500, 3), 200, dtype=np.uint8),
                                     0.1, larger_area)
        self.assertEqual(observation.scene_change_percent, 0)

    def test_small_camera_crop_size_change_keeps_reference(self):
        vision = self.make_vision()
        first_area = ScanArea(((20, 20), (380, 20), (380, 280), (20, 280)))
        slightly_larger_area = ScanArea(((20, 20), (384, 20), (384, 282), (20, 282)))
        old_page = np.full((300, 400, 3), 60, dtype=np.uint8)
        vision.analyze(old_page, 0, first_area)
        new_page = np.full((303, 404, 3), 200, dtype=np.uint8)
        observation = vision.analyze(new_page, 0.1, slightly_larger_area)
        self.assertGreater(observation.scene_change_percent, 90)

    def test_motion_outside_manual_selection_is_ignored(self):
        vision = self.make_vision()
        area = ScanArea(((180, 120), (620, 120), (620, 460), (180, 460)))
        frame = np.full((600, 800, 3), 60, dtype=np.uint8)
        vision.analyze(frame, 0, area)
        frame[:, :120] = 200
        outside = vision.analyze(frame, 0.1, area)
        self.assertEqual(outside.scene_change_percent, 0)
        self.assertEqual(outside.motion_percent, 0)
        frame[200:380, 250:550] = 200
        self.assertGreater(vision.analyze(frame, 0.2, area).scene_change_percent, 10)


if __name__ == "__main__":
    unittest.main()
