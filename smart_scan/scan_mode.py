from __future__ import annotations

from enum import Enum

import cv2
import numpy as np


class ScanMode(str, Enum):
    DOCUMENT = "document"
    BOOK = "book"
    SELECT_AREA = "select_area"
    IDENTIFICATION = "identification"
    ORIGINAL_IMAGE = "original_image"


def _radio_centers(mask: np.ndarray, left: int, right: int) -> list[tuple[float, float]]:
    count, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
    centers = []
    for (x, y, width, height, pixels), (center_x, center_y) in zip(
            stats[1:count], centroids[1:count]):
        if (left <= x and x + width <= right and
                10 <= width <= 20 and 10 <= height <= 20 and
                0.7 <= width / height <= 1.3 and
                pixels >= 0.6 * width * height):
            centers.append((float(center_x), float(center_y)))
    return centers


def detect_scan_mode(window_frame: np.ndarray,
                     camera_rect: tuple[int, int, int, int]) -> ScanMode | None:
    """Read the selected Libera Scan Mode from its five aligned radio buttons."""
    height, width = window_frame.shape[:2]
    panel_left = camera_rect[2] + 15
    panel_right = width - 20
    if panel_right - panel_left < 50 or height < 300:
        return None

    panel = window_frame[:, panel_left:panel_right]
    hsv = cv2.cvtColor(panel, cv2.COLOR_BGR2HSV)
    orange = cv2.inRange(hsv, (5, 130, 100), (25, 255, 255))
    white = cv2.inRange(panel, (175, 175, 175), (255, 255, 255))
    blue_gray = cv2.inRange(panel, (120, 100, 80), (210, 190, 170))
    blue_gray &= ((panel[:, :, 0].astype(np.int16) - panel[:, :, 1] > 8) &
                  (panel[:, :, 1].astype(np.int16) - panel[:, :, 2] > 8)).astype(np.uint8) * 255
    selected = _radio_centers(orange, 0, panel.shape[1])
    inactive = _radio_centers(cv2.bitwise_or(white, blue_gray), 0, panel.shape[1])
    modes = tuple(ScanMode)

    for selected_x, selected_y in selected:
        aligned = [(selected_y, True)]
        aligned.extend((y, False) for x, y in inactive if abs(x - selected_x) <= 3)
        aligned.sort()
        for start in range(len(aligned) - len(modes) + 1):
            row = aligned[start:start + len(modes)]
            if sum(is_selected for _, is_selected in row) != 1:
                continue
            gaps = np.diff([y for y, _ in row])
            if (35 <= float(gaps.mean()) <= 110 and
                    float(gaps.max() - gaps.min()) <= max(5, float(gaps.mean()) * 0.18)):
                return modes[next(i for i, (_, is_selected) in enumerate(row)
                                  if is_selected)]
    return None
