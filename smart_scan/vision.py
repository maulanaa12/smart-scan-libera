from __future__ import annotations

import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from .core import HandStatus, Observation
from .camera_readiness import CameraReadiness
from .finger_edges import box_allowed, edge_skin_boxes
from .scan_area import ScanArea


class VisionAnalyzer:
    def __init__(self, motion_cfg: dict, hand_cfg: dict, camera_cfg: dict, project_dir: Path):
        model_path = project_dir / hand_cfg["model_path"]
        if not model_path.is_file():
            raise FileNotFoundError(f"Model tangan tidak ada: {model_path}")
        zones = hand_cfg["allowed_zones"]
        if not zones or any(len(z) != 4 or not (0 <= z[0] < z[2] <= 1 and 0 <= z[1] < z[3] <= 1) for z in zones):
            raise ValueError("hands.allowed_zones harus berisi [kiri, atas, kanan, bawah] pada rentang 0..1")
        self.zones = zones
        self.pixel_delta = int(motion_cfg["pixel_delta"])
        self.inference_width = int(hand_cfg["inference_width"])
        self.blocked_grace = float(hand_cfg["blocked_grace_seconds"])
        self.edge_skin_fallback = bool(hand_cfg["edge_skin_fallback"])
        self.edge_skin_min_area = float(hand_cfg["edge_skin_min_area_percent"])
        self.last_blocked_at = float("-inf")
        self.camera = CameraReadiness(camera_cfg)
        self.prev_gray: np.ndarray | None = None
        self.reference_gray: np.ndarray | None = None
        self.last_mask: np.ndarray | None = None
        self.reference_mask: np.ndarray | None = None
        self.frame_size: tuple[int, int] | None = None
        self.last_model_timestamp = -1
        scene_mask = np.ones((180, 320), dtype=np.uint8)
        for left, top, right, bottom in zones:
            x1, x2 = int(left * 320), int(right * 320)
            y1, y2 = int(top * 180), int(bottom * 180)
            scene_mask[y1:y2, x1:x2] = 0
        if not np.any(scene_mask):
            raise ValueError("Zona tangan menutupi seluruh bidang analisis")

        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=int(hand_cfg["max_hands"]),
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)

    def close(self) -> None:
        self.landmarker.close()

    def accept_scene(self) -> None:
        if self.prev_gray is not None and self.last_mask is not None:
            self.reference_gray = self.prev_gray.copy()
            self.reference_mask = self.last_mask.copy()

    def reset_motion(self, reset_camera: bool = True) -> None:
        self.prev_gray = None
        self.reference_gray = None
        self.last_mask = None
        self.reference_mask = None
        self.frame_size = None
        if reset_camera:
            self.camera.reset()

    def _area_mask(self, area: ScanArea, frame_size: tuple[int, int]) -> np.ndarray:
        height, width = frame_size

        def polygon(bounds: tuple[float, float, float, float]) -> np.ndarray:
            left, top, right, bottom = bounds
            points = [area.point(u, v) for u, v in
                      ((left, top), (right, top), (right, bottom), (left, bottom))]
            return np.asarray([(round(x * 320 / width), round(y * 180 / height))
                               for x, y in points], dtype=np.int32)

        mask = np.zeros((180, 320), dtype=np.uint8)
        cv2.fillConvexPoly(mask, polygon((0.01, 0.01, 0.99, 0.99)), 1)
        for zone in self.zones:
            cv2.fillConvexPoly(mask, polygon(tuple(zone)), 0)
        return mask.astype(bool)

    def _hand_status(self, frame: np.ndarray, now: float) -> HandStatus:
        h, w = frame.shape[:2]
        scale = min(1.0, self.inference_width / max(w, h))
        target_w = max(1, round(w * scale))
        target_h = max(1, round(h * scale))
        resized = cv2.resize(frame, (target_w, target_h))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        timestamp = max(self.last_model_timestamp + 1, time.monotonic_ns() // 1_000_000)
        self.last_model_timestamp = timestamp
        result = self.landmarker.detect_for_video(image, timestamp)
        if not result.hand_landmarks:
            if now - self.last_blocked_at < self.blocked_grace:
                return HandStatus.BLOCKED
            if self.edge_skin_fallback:
                boxes = edge_skin_boxes(resized, self.edge_skin_min_area)
                if any(not box_allowed(box, self.zones) for box in boxes):
                    return HandStatus.UNKNOWN
                if boxes:
                    return HandStatus.ALLOWED
            return HandStatus.CLEAR

        for hand in result.hand_landmarks:
            box = (min(point.x for point in hand), min(point.y for point in hand),
                   max(point.x for point in hand), max(point.y for point in hand))
            if not box_allowed(box, self.zones):
                self.last_blocked_at = now
                return HandStatus.BLOCKED
        return HandStatus.ALLOWED

    def analyze(self, frame: np.ndarray, now: float,
                area: ScanArea | None) -> Observation:
        if not self.camera.update(frame, now):
            self.reset_motion(reset_camera=False)
            return Observation(0, 0, HandStatus.UNKNOWN, False)
        if area is None:
            self.prev_gray = None
            self.last_mask = None
            return Observation(0, 0, HandStatus.UNKNOWN, True, False)
        if self.frame_size is not None:
            size_change = max(abs(new - old) / old for new, old in
                              zip(frame.shape[:2], self.frame_size))
            if size_change > 0.02:
                self.reset_motion(reset_camera=False)
        self.frame_size = frame.shape[:2]
        mask = self._area_mask(area, self.frame_size)
        mask_size = np.count_nonzero(mask)
        if mask_size < 100:
            self.prev_gray = None
            self.last_mask = None
            return Observation(0, 0, HandStatus.UNKNOWN, True, False)
        small = cv2.resize(frame, (320, 180))
        gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (15, 15), 0)
        motion = 0.0
        if self.prev_gray is not None:
            changed = (cv2.absdiff(gray, self.prev_gray) > self.pixel_delta).astype(np.uint8)
            changed = cv2.morphologyEx(changed, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            motion = float(np.count_nonzero(changed & mask) * 100 / mask_size)
        self.prev_gray = gray
        self.last_mask = mask

        if self.reference_gray is None:
            self.reference_gray = gray.copy()
            self.reference_mask = mask.copy()
        comparison_mask = mask & self.reference_mask
        comparison_size = np.count_nonzero(comparison_mask)
        if comparison_size < 0.75 * min(mask_size, np.count_nonzero(self.reference_mask)):
            self.reference_gray = gray.copy()
            self.reference_mask = mask.copy()
            comparison_mask = mask
            comparison_size = mask_size
        changed_scene = cv2.absdiff(gray, self.reference_gray) > self.pixel_delta
        scene_delta = float(np.count_nonzero(changed_scene & comparison_mask) * 100 /
                            comparison_size)

        try:
            hand = self._hand_status(area.extract(frame), now)
        except Exception:
            hand = HandStatus.UNKNOWN
        return Observation(motion, scene_delta, hand)
