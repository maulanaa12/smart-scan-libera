from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class State(str, Enum):
    WAIT_CAMERA = "KAMERA BELUM SIAP"
    WAIT_AREA = "AREA SCAN BELUM TERDETEKSI"
    IDLE = "SIAP"
    MOVING = "MENATA HALAMAN"
    SETTLING = "MENUNGGU STABIL"
    BLOCKED = "TANGAN DI AREA ISI"
    UNCERTAIN = "PERIKSA MANUAL"
    COOLDOWN = "MEMPROSES SCAN"
    PAUSED = "DIJEDA"


class HandStatus(str, Enum):
    CLEAR = "clear"
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Observation:
    motion_percent: float
    scene_change_percent: float
    hand: HandStatus
    frame_valid: bool = True
    area_valid: bool = True


@dataclass(frozen=True)
class Decision:
    state: State
    trigger: bool = False
    progress: float = 0.0


class ScanController:
    def __init__(self, motion_cfg: dict):
        self.turn_threshold = float(motion_cfg["turn_threshold_percent"])
        self.quiet_threshold = float(motion_cfg["quiet_threshold_percent"])
        self.scene_threshold = float(motion_cfg["scene_change_percent"])
        self.settle_seconds = float(motion_cfg["debounce_seconds"])
        self.cooldown_seconds = float(motion_cfg["cooldown_seconds"])
        if not 0 < self.quiet_threshold < self.turn_threshold:
            raise ValueError("quiet_threshold_percent harus lebih kecil dari turn_threshold_percent")
        if self.settle_seconds <= 0 or self.cooldown_seconds < 0:
            raise ValueError("Durasi stabilisasi harus positif; cooldown tidak boleh negatif")
        self.state = State.IDLE
        self.stable_since: float | None = None
        self.cooldown_until = 0.0
        self.paused = False

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.state = State.PAUSED if self.paused else State.IDLE
        self.stable_since = None

    def manual_trigger(self, now: float) -> None:
        self.state = State.COOLDOWN
        self.cooldown_until = now + self.cooldown_seconds
        self.stable_since = None

    def reset_for_mode(self, now: float) -> None:
        self.stable_since = None
        if self.paused:
            self.state = State.PAUSED
        elif now < self.cooldown_until:
            self.state = State.COOLDOWN
        else:
            self.state = State.WAIT_AREA

    def update(self, obs: Observation, now: float) -> Decision:
        if self.paused:
            return Decision(State.PAUSED)
        if not obs.frame_valid:
            self.stable_since = None
            self.state = State.WAIT_CAMERA
            return Decision(self.state)
        if not obs.area_valid:
            self.stable_since = None
            self.state = State.WAIT_AREA
            return Decision(self.state)
        if now < self.cooldown_until:
            self.stable_since = None
            self.state = State.COOLDOWN
            return Decision(self.state)
        if self.state == State.WAIT_CAMERA:
            self.state = State.IDLE
            return Decision(self.state)
        if self.state == State.WAIT_AREA:
            self.state = State.IDLE
        if self.state == State.COOLDOWN:
            self.state = State.IDLE

        changed = obs.scene_change_percent >= self.scene_threshold
        moving = obs.motion_percent >= self.turn_threshold
        quiet = obs.motion_percent <= self.quiet_threshold

        if self.state == State.IDLE:
            if moving and changed:
                self.state = State.MOVING
            elif quiet and changed:
                self.state = State.SETTLING
                self.stable_since = now
            return Decision(self.state)

        if self.state == State.MOVING:
            if not changed:
                self.state = State.IDLE
            elif quiet:
                self.state = State.SETTLING
                self.stable_since = None
            return Decision(self.state)

        if not changed:
            self.state = State.IDLE
            self.stable_since = None
            return Decision(self.state)
        if not quiet:
            self.state = State.MOVING
            self.stable_since = None
            return Decision(self.state)
        if obs.hand == HandStatus.UNKNOWN:
            self.state = State.UNCERTAIN
            self.stable_since = None
            return Decision(self.state)
        if obs.hand == HandStatus.BLOCKED:
            self.state = State.BLOCKED
            self.stable_since = None
            return Decision(self.state)

        self.state = State.SETTLING
        if self.stable_since is None:
            self.stable_since = now
        elapsed = now - self.stable_since
        progress = min(1.0, elapsed / self.settle_seconds)
        if elapsed >= self.settle_seconds:
            self.manual_trigger(now)
            return Decision(State.COOLDOWN, trigger=True, progress=1.0)
        return Decision(self.state, progress=progress)
