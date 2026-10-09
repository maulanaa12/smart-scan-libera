from __future__ import annotations

import cv2
import numpy as np


class CameraReadiness:
    def __init__(self, config: dict):
        self.max_dominant = float(config["max_dominant_color_percent"]) / 100
        self.min_std = float(config["min_gray_std"])
        self.ready_seconds = float(config["ready_seconds"])
        self.stale_seconds = float(config["stale_seconds"])
        if not 0 < self.max_dominant < 1 or self.min_std < 0:
            raise ValueError("Pengaturan camera_readiness tidak valid")
        self.reset()

    def reset(self) -> None:
        self.reason = "Menunggu gambar kamera"
        self.ready = False
        self.candidate_since: float | None = None
        self.last_raw: bytes | None = None
        self.last_new_at: float | None = None

    def update(self, frame: np.ndarray | None, now: float) -> bool:
        if frame is None or frame.size == 0:
            self.reset()
            return False
        small = cv2.resize(frame, (160, 90))
        gray_std = float(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).std())
        b, g, r = cv2.split(small >> 4)
        bins = (b.astype(np.int32) << 8) | (g.astype(np.int32) << 4) | r.astype(np.int32)
        dominant = np.bincount(bins.ravel(), minlength=4096).max() / bins.size
        if dominant > self.max_dominant or gray_std < self.min_std:
            self.reset()
            self.reason = "Gambar terlalu seragam; periksa seluruh kamera dengan tombol C"
            return False

        raw = small.tobytes()
        if raw != self.last_raw:
            self.last_raw = raw
            self.last_new_at = now
        if self.last_new_at is None or now - self.last_new_at > self.stale_seconds:
            self.reset()
            self.reason = "Gambar tidak berubah; periksa pratinjau kamera Libera"
            return False
        if self.candidate_since is None:
            self.candidate_since = now
        self.ready = now - self.candidate_since >= self.ready_seconds
        self.reason = "Siap" if self.ready else "Menunggu gambar kamera stabil selama satu detik"
        return self.ready
