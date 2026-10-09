from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .scan_mode import ScanMode


@dataclass(frozen=True)
class ScanArea:
    # Top-left, top-right, bottom-right, bottom-left in camera coordinates.
    corners: tuple[tuple[int, int], ...]

    def point(self, u: float, v: float) -> tuple[int, int]:
        tl, tr, br, bl = np.asarray(self.corners, dtype=np.float32)
        point = (1 - v) * ((1 - u) * tl + u * tr) + v * ((1 - u) * bl + u * br)
        return int(round(float(point[0]))), int(round(float(point[1])))

    def extract(self, frame: np.ndarray) -> np.ndarray:
        tl, tr, br, bl = np.asarray(self.corners, dtype=np.float32)
        width = max(8, round((np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2))
        height = max(8, round((np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2))
        destination = np.float32([[0, 0], [width - 1, 0],
                                  [width - 1, height - 1], [0, height - 1]])
        matrix = cv2.getPerspectiveTransform(np.float32([tl, tr, br, bl]), destination)
        straight = cv2.warpPerspective(frame, matrix, (width, height))
        return straight[2:-2, 2:-2]


def full_frame_area(frame: np.ndarray) -> ScanArea:
    height, width = frame.shape[:2]
    return ScanArea(((0, 0), (width - 1, 0),
                     (width - 1, height - 1), (0, height - 1)))


def manual_selected_area(frame: np.ndarray) -> ScanArea | None:
    """Read the closed red rectangle drawn by Libera's Select Area tool."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    red = cv2.bitwise_or(cv2.inRange(hsv, (0, 140, 80), (8, 255, 255)),
                        cv2.inRange(hsv, (172, 140, 80), (179, 255, 255)))
    connected = cv2.morphologyEx(red, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(connected, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        points = cv2.approxPolyDP(contour, perimeter * 0.02, True).reshape(-1, 2)
        if len(points) != 4 or not cv2.isContourConvex(points):
            continue
        x1, y1 = points.min(axis=0)
        x2, y2 = points.max(axis=0)
        width, height = int(x2 - x1), int(y2 - y1)
        if width < 40 or height < 40:
            continue
        corners = np.array(((x1, y1), (x2, y1), (x2, y2), (x1, y2)))
        if any(np.min(np.max(np.abs(points - corner), axis=1)) > 3 for corner in corners):
            continue
        top = red[max(0, y1 - 2):y1 + 3, x1:x2 + 1].any(axis=0).mean()
        bottom = red[max(0, y2 - 2):y2 + 3, x1:x2 + 1].any(axis=0).mean()
        left = red[y1:y2 + 1, max(0, x1 - 2):x1 + 3].any(axis=1).mean()
        right = red[y1:y2 + 1, max(0, x2 - 2):x2 + 3].any(axis=1).mean()
        interior = red[y1 + 4:y2 - 3, x1 + 4:x2 - 3]
        if min(top, bottom, left, right) < 0.85 or np.mean(interior != 0) > 0.2:
            continue
        candidates.append((width * height, ScanArea(tuple(map(tuple, corners.tolist())))))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def area_for_mode(frame: np.ndarray, mode: ScanMode | None,
                  previous_mode: ScanMode | None = None,
                  selecting: bool = False) -> ScanArea | None:
    if mode in (ScanMode.ORIGINAL_IMAGE, ScanMode.BOOK):
        return full_frame_area(frame)
    if mode == ScanMode.SELECT_AREA:
        return None if selecting else manual_selected_area(frame)
    if mode is None and previous_mode in (
            ScanMode.ORIGINAL_IMAGE, ScanMode.BOOK, ScanMode.SELECT_AREA):
        return None
    return selected_area(frame)


def selected_area(frame: np.ndarray) -> ScanArea | None:
    """Find Libera's orange scan selection, including slanted quadrilaterals."""
    height, width = frame.shape[:2]
    if height < 150 or width < 200:
        return None

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    orange = cv2.inRange(hsv, (5, 180, 80), (24, 255, 255))
    ys, xs = np.where(orange != 0)
    if len(xs) < height * 0.5:
        return None
    x_min, x_max = int(xs.min()), int(xs.max())
    y_min, y_max = int(ys.min()), int(ys.max())
    if x_max - x_min < width * 0.12 or y_max - y_min < height * 0.8:
        return None

    lines = cv2.HoughLinesP(orange, 1, np.pi / 180,
                            max(20, round(height * 0.04)),
                            minLineLength=max(40, round(height * 0.10)),
                            maxLineGap=max(15, round(height * 0.12)))
    if lines is None:
        return None
    vertical = []
    horizontal = []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        dx, dy = abs(int(x2 - x1)), abs(int(y2 - y1))
        if dy >= height * 0.25 and dx <= dy * 0.2:
            vertical.append(((x1 + x2) / 2, dy, (x1, y1, x2, y2)))
        if dx >= width * 0.12 and dy <= dx * 0.2:
            horizontal.append(((y1 + y2) / 2, dx, (x1, y1, x2, y2)))
    if not vertical or not horizontal:
        return None

    left = min(vertical, key=lambda line: line[0])
    right = max(vertical, key=lambda line: line[0])
    if right[0] - left[0] < width * 0.12:
        if x_min <= width * 0.03 and x_max - right[0] >= width * 0.12:
            right = (float(x_max), 0, (x_max, y_min, x_max, y_max))
        elif left[0] - x_min >= width * 0.12 and x_min <= width * 0.03:
            left = (float(x_min), 0, (x_min, y_min, x_min, y_max))
        else:
            return None

    def best_line(anchor, candidates):
        nearby = [line for line in candidates if abs(line[0] - anchor[0]) <=
                  (width * 0.04 if candidates is vertical else height * 0.04)]
        return max(nearby, key=lambda line: line[1])[2] if nearby else anchor[2]

    left_line = best_line(left, vertical)
    right_line = best_line(right, vertical)
    top_line = best_line(min(horizontal, key=lambda line: line[0]), horizontal)
    bottom_line = best_line(max(horizontal, key=lambda line: line[0]), horizontal)
    if abs((bottom_line[1] + bottom_line[3]) / 2 -
           (top_line[1] + top_line[3]) / 2) < height * 0.3:
        line_y = (top_line[1] + top_line[3]) / 2
        if abs(line_y - y_min) <= abs(line_y - y_max):
            bottom_line = (x_min, y_max, x_max, y_max)
        else:
            top_line = (x_min, y_min, x_max, y_min)

    def intersection(vertical_line, horizontal_line):
        x1, y1, x2, y2 = map(float, vertical_line)
        x3, y3, x4, y4 = map(float, horizontal_line)
        a = np.array([[y2 - y1, x1 - x2], [y4 - y3, x3 - x4]], dtype=np.float64)
        b = np.array([x1 * (y2 - y1) + y1 * (x1 - x2),
                      x3 * (y4 - y3) + y3 * (x3 - x4)], dtype=np.float64)
        if abs(np.linalg.det(a)) < 1:
            return None
        x, y = np.linalg.solve(a, b)
        if not (-width * 0.03 <= x <= width * 1.03 and
                -height * 0.03 <= y <= height * 1.03):
            return None
        return (int(np.clip(round(x), 0, width - 1)),
                int(np.clip(round(y), 0, height - 1)))

    corners = [intersection(left_line, top_line), intersection(right_line, top_line),
               intersection(right_line, bottom_line), intersection(left_line, bottom_line)]
    if any(point is None for point in corners) or len(set(corners)) != 4:
        return None
    if (min(corners[2][1], corners[3][1]) - max(corners[0][1], corners[1][1]) <
            height * 0.75):
        return None
    return ScanArea(tuple(corners))
