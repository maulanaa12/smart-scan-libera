import unittest

import cv2
import numpy as np

from smart_scan.camera_readiness import CameraReadiness


CONFIG = {
    "max_dominant_color_percent": 70,
    "min_gray_std": 15,
    "ready_seconds": 1.0,
    "stale_seconds": 1.5,
}


class CameraReadinessTests(unittest.TestCase):
    def setUp(self):
        self.gate = CameraReadiness(CONFIG)
        rng = np.random.default_rng(7)
        self.camera = rng.integers(20, 230, (180, 320, 3), dtype=np.uint8)

    def test_no_device_placeholder_is_rejected_immediately(self):
        placeholder = np.full((180, 320, 3), (52, 55, 61), dtype=np.uint8)
        cv2.putText(placeholder, "No device found", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2)
        self.assertFalse(self.gate.update(placeholder, 0))
        self.assertFalse(self.gate.update(placeholder, 10))

    def test_camera_needs_warmup_and_disconnection_resets_it(self):
        self.assertFalse(self.gate.update(self.camera, 0))
        self.assertFalse(self.gate.update(self.camera, 0.5))
        self.assertTrue(self.gate.update(self.camera, 1.0))
        self.assertFalse(self.gate.update(None, 1.1))
        self.assertFalse(self.gate.update(self.camera, 1.2))
        self.assertTrue(self.gate.update(self.camera, 2.3))

    def test_frozen_frame_is_rejected(self):
        self.assertFalse(self.gate.update(self.camera, 0))
        self.assertTrue(self.gate.update(self.camera, 1.0))
        self.assertFalse(self.gate.update(self.camera, 1.6))


if __name__ == "__main__":
    unittest.main()
