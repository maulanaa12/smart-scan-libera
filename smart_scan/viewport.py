from __future__ import annotations

import cv2
import numpy as np


def validate_layout(layout: dict) -> None:
    left = int(layout["sidebar_width_px"])
    right = int(layout["controls_width_px"])
    top = int(layout["toolbar_height_px"])
    aspect = float(layout["camera_aspect_ratio"])
    if left < 0 or right < 0 or top < 0 or not 1.0 <= aspect <= 2.0:
        raise ValueError("Ukuran tata letak kamera tidak valid")


def _scanline_camera_rect(image: np.ndarray, background: np.ndarray,
                          layout: dict) -> tuple[int, int, int, int] | None:
    """Infer a 4:3 preview from its vertical edges and gray margins."""
    height, width = image.shape[:2]
    top = int(layout["toolbar_height_px"])
    expected_left = int(layout["sidebar_width_px"])
    aspect = float(layout["camera_aspect_ratio"])

    bottom_strip = image[max(top, height - 80):height - 10,
                         :min(width, expected_left + 60)]
    if bottom_strip.size == 0:
        return None
    white_fraction = np.mean(np.all(bottom_strip >= 235, axis=2), axis=0)
    near_sidebar = range(max(5, expected_left - 60),
                         min(len(white_fraction) - 5, expected_left + 60))
    boundaries = [x for x in near_sidebar
                  if white_fraction[x - 5:x].mean() > 0.8 and
                  white_fraction[x:x + 5].mean() < 0.2]
    sidebar_end = min(boundaries, key=lambda x: abs(x - expected_left)) if boundaries else expected_left

    low = np.maximum(background.astype(np.int16) - 12, 0).astype(np.uint8)
    high = np.minimum(background.astype(np.int16) + 12, 255).astype(np.uint8)
    foreground = cv2.bitwise_not(cv2.inRange(image, low, high)) != 0
    for x in range(sidebar_end + 5, width - 20, 8):
        column = foreground[top:height, x]
        transitions = np.diff(np.r_[False, column, False].astype(np.int8))
        starts = np.flatnonzero(transitions == 1)
        ends = np.flatnonzero(transitions == -1)
        if not len(starts):
            continue
        lengths = ends - starts
        index = int(np.argmax(lengths))
        y1, y2 = top + int(starts[index]), top + int(ends[index])
        if (y2 - y1 < max(150, (height - top) * 0.25) or
                y1 <= top + 12 or y2 >= height - 12):
            continue
        row = foreground[(y1 + y2) // 2, sidebar_end:x + 1]
        if not row[-1]:
            continue
        first = len(row) - int(np.flatnonzero(~row[::-1])[0]) if np.any(~row) else 0
        x1 = sidebar_end + first
        x2 = x1 + round((y2 - y1) * aspect)
        if x2 > width or x2 - x1 < 200:
            continue
        # Both horizontal borders must be visible across the inferred width.
        if (foreground[y1 - 3:y1, x1:x2].mean() > 0.15 or
                foreground[y2:y2 + 3, x1:x2].mean() > 0.15):
            continue
        return x1, y1, x2, y2
    return None


def find_camera_rect(window_image: np.ndarray, layout: dict) -> tuple[int, int, int, int] | None:
    """Locate the camera pixels on Libera's uniform gray workspace."""
    validate_layout(layout)
    height, width = window_image.shape[:2]
    left = int(layout["sidebar_width_px"])
    right = int(layout["controls_width_px"])
    top = int(layout["toolbar_height_px"])
    x_end = width - right if right else width - 10
    if width - left < 250 or height - top < 200 or x_end <= left:
        return None

    roi = window_image[top:height, left:x_end]
    aspect = float(layout["camera_aspect_ratio"])
    sample_positions = [left + 5]
    if right >= 20 and width - right + 13 <= width:
        sample_positions.append(width - right + 5)
    for sample_x in sample_positions:
        sample = window_image[top + 5:top + 13, sample_x:sample_x + 8]
        background = np.median(sample.reshape(-1, 3), axis=0).astype(np.uint8)
        if not 25 <= float(background.mean()) <= 100 or int(background.max()) - int(background.min()) > 30:
            continue
        scanline = _scanline_camera_rect(window_image, background, layout)
        if scanline is not None:
            return scanline
        low = np.maximum(background.astype(np.int16) - 12, 0).astype(np.uint8)
        high = np.minimum(background.astype(np.int16) + 12, 255).astype(np.uint8)
        different = cv2.bitwise_not(cv2.inRange(roi, low, high))
        different = cv2.morphologyEx(different, cv2.MORPH_CLOSE,
                                      np.ones((9, 9), np.uint8))
        count, _, stats, _ = cv2.connectedComponentsWithStats(different)
        candidates = []
        for x, y, w, h, pixels in stats[1:count]:
            if w < 200 or h < 150 or pixels < w * h * 0.65:
                continue
            if abs(w / h - aspect) > 0.12:
                continue
            candidates.append((int(pixels), (left + int(x), top + int(y),
                                             left + int(x + w), top + int(y + h))))
        if candidates:
            return max(candidates)[1]
    return None
