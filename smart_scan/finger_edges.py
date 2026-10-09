from __future__ import annotations

import cv2
import numpy as np


def edge_skin_boxes(frame: np.ndarray, min_area_percent: float) -> list[tuple[float, float, float, float]]:
    """Find skin-like connected areas entering from the camera frame edge."""
    h, w = frame.shape[:2]
    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    chroma = cv2.inRange(ycrcb, np.array([0, 133, 77]), np.array([255, 173, 127])) > 0
    b, g, r = (channel.astype(np.int16) for channel in cv2.split(frame))
    rgb = (r > 90) & (g > 40) & (b > 20) & (r > g) & (r > b + 15) & (np.abs(r - g) > 15)
    mask = (chroma & rgb).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    boxes = []
    minimum = h * w * min_area_percent / 100
    edge_x, edge_y = max(2, int(w * 0.02)), max(2, int(h * 0.02))
    for index in range(1, count):
        x, y, width, height, area = stats[index]
        if area < minimum:
            continue
        if x > edge_x and y > edge_y and x + width < w - edge_x and y + height < h - edge_y:
            continue
        sheet_like = (y <= edge_y and width >= w * 0.35 and height >= h * 0.72 and
                      area >= h * w * 0.18 and area >= width * height * 0.55)
        if sheet_like:
            continue
        boxes.append((x / w, y / h, (x + width) / w, (y + height) / h))
    return boxes


def box_allowed(box: tuple[float, float, float, float], zones: list[list[float]]) -> bool:
    left, top, right, bottom = box
    return any(z[0] <= left and z[1] <= top and right <= z[2] and bottom <= z[3]
               for z in zones)
