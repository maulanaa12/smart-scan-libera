from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from smart_scan.core import HandStatus, Observation, ScanController, State
from smart_scan.scan_area import ScanArea, area_for_mode
from smart_scan.scan_mode import ScanMode
from smart_scan.vision import VisionAnalyzer


ROOT = Path(__file__).resolve().parent
AREA_RECOVERY_SECONDS = 3.0
PIN_BUTTON_HEIGHT = 34
PIN_BUTTON_WIDTH = 104


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        config = json.load(file)
    from smart_scan.viewport import validate_layout

    validate_layout(config["window"]["camera_layout"])
    return config


def draw_hud(frame, decision, observation, scan_count: int, zones: list, dry_run: bool,
             preview_width: int, preview_height: int,
             analysis_area: ScanArea | None = None, note: str | None = None,
             pinned: bool = False):
    header_height = 72
    footer_height = 42
    output = np.full((header_height + preview_height + footer_height, preview_width, 3),
                     (26, 26, 26), dtype=np.uint8)
    frame_height, frame_width = frame.shape[:2]
    scale = min(preview_width / frame_width, preview_height / frame_height)
    image_width = max(1, round(frame_width * scale))
    image_height = max(1, round(frame_height * scale))
    image_left = (preview_width - image_width) // 2
    image_top = header_height + (preview_height - image_height) // 2
    output[image_top:image_top + image_height, image_left:image_left + image_width] = cv2.resize(
        frame, (image_width, image_height))
    if observation.frame_valid and analysis_area is not None:
        def hud_point(x: int, y: int) -> tuple[int, int]:
            return (image_left + round(x * image_width / frame_width),
                    image_top + round(y * image_height / frame_height))

        outline = np.array([hud_point(x, y) for x, y in analysis_area.corners], np.int32)
        cv2.polylines(output, [outline], True, (0, 220, 255), 2)
        for left, top, right, bottom in zones:
            zone = np.array([hud_point(*analysis_area.point(u, v)) for u, v in
                             ((left, top), (right, top), (right, bottom), (left, bottom))],
                            np.int32)
            cv2.polylines(output, [zone], True, (0, 180, 0), 2)
    color = {
        State.WAIT_CAMERA: (0, 0, 255), State.WAIT_AREA: (0, 0, 255),
        State.IDLE: (50, 210, 50),
        State.MOVING: (0, 210, 255),
        State.SETTLING: (255, 200, 0), State.BLOCKED: (0, 130, 255),
        State.UNCERTAIN: (0, 0, 255), State.COOLDOWN: (200, 200, 200),
        State.PAUSED: (150, 150, 150),
    }[decision.state]
    cv2.rectangle(output, (0, 0), (preview_width, header_height - 1), (24, 24, 24), -1)
    cv2.putText(output, decision.state.value, (12, 27), cv2.FONT_HERSHEY_SIMPLEX,
                0.72, color, 2)
    count_label = "Simulasi" if dry_run else "Perintah scan"
    status_line = note or (f"{count_label}: {scan_count}  Motion: {observation.motion_percent:.1f}%"
                          f"  Scene: {observation.scene_change_percent:.1f}%  Hand: {observation.hand.value}")
    cv2.putText(output, status_line,
                (12, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (230, 230, 230), 1)
    pin_left = preview_width - PIN_BUTTON_WIDTH - 12
    pin_color = (45, 125, 210) if pinned else (70, 70, 70)
    cv2.rectangle(output, (pin_left, 7),
                  (preview_width - 12, 7 + PIN_BUTTON_HEIGHT), pin_color, -1)
    cv2.putText(output, "PIN: ON" if pinned else "PIN: OFF", (pin_left + 10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    if decision.state == State.SETTLING:
        cv2.rectangle(output, (0, header_height - 5),
                      (int(preview_width * decision.progress), header_height - 1), color, -1)
    footer_top = header_height + preview_height
    cv2.rectangle(output, (0, footer_top), (preview_width, output.shape[0]), (24, 24, 24), -1)
    label = "P: jeda  S: scan manual  C: pilih kamera  T: pin  Q: keluar"
    if dry_run:
        label += "  |  SIMULASI"
    cv2.putText(output, label, (12, output.shape[0] - 14), cv2.FONT_HERSHEY_SIMPLEX,
                0.52, (220, 220, 220), 1)
    return output


def pin_button_hit(x: int, y: int, preview_width: int) -> bool:
    return preview_width - PIN_BUTTON_WIDTH - 12 <= x <= preview_width - 12 and 7 <= y <= 7 + PIN_BUTTON_HEIGHT


def set_hud_pin(window_name: str, pinned: bool) -> bool:
    try:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1 if pinned else 0)
        return cv2.getWindowProperty(window_name, cv2.WND_PROP_TOPMOST) == int(pinned)
    except cv2.error:
        return False


def calibrate_camera(window) -> bool:
    frame = window.last_window_frame
    if frame is None:
        print("[KALIBRASI] Tangkapan jendela Libera belum tersedia")
        return False
    height, width = frame.shape[:2]
    scale = min(1.0, 800 / width, 550 / height)
    preview = cv2.resize(frame, (round(width * scale), round(height * scale)))
    name = "Pilih SELURUH kamera - tarik kotak, Enter simpan, Esc batal"
    try:
        x, y, w, h = cv2.selectROI(name, preview, showCrosshair=True, fromCenter=False)
    finally:
        cv2.destroyWindow(name)
    if w < 20 or h < 20:
        return False
    sx, sy = width / preview.shape[1], height / preview.shape[0]
    window.manual_camera_rect = (round(x * sx), round(y * sy),
                                 min(width, round((x + w) * sx)),
                                 min(height, round((y + h) * sy)))
    window.manual_window_size = (width, height)
    print(f"[KALIBRASI] Bidang kamera: {window.manual_camera_rect}; ukuran jendela: {width}x{height}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Pendamping auto-scan untuk Libera Scanner")
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--dry-run", action="store_true", help="Analisis tanpa mengirim perintah scan")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Penangkapan jendela Libera membutuhkan Windows")

    from smart_scan.win32_libera import LiberaWindow

    config = load_config(args.config)
    controller = ScanController(config["motion"])
    vision = VisionAnalyzer(config["motion"], config["hands"], config["camera_readiness"], ROOT)
    window = LiberaWindow(config["window"])
    preview_w = int(config["ui"]["preview_width"])
    preview_h = int(config["ui"]["preview_height"])
    hud_name = "Smart Scan Libera"
    cv2.namedWindow(hud_name, cv2.WINDOW_AUTOSIZE)
    pinned = False

    def toggle_pin() -> None:
        nonlocal pinned
        wanted = not pinned
        if set_hud_pin(hud_name, wanted):
            pinned = wanted
            print(f"[HUD] Pin {'aktif' if pinned else 'nonaktif'}")
        else:
            print("[WARN] Pengaturan pin jendela HUD gagal")

    def on_hud_mouse(event, x, y, flags, userdata) -> None:
        if event == cv2.EVENT_LBUTTONUP and pin_button_hit(x, y, preview_w):
            toggle_pin()

    cv2.setMouseCallback(hud_name, on_hud_mouse)
    count = 0
    last_state = None
    last_search = 0.0
    last_area = None
    last_manual_area = None
    last_mode = None
    pending_mode_scan = False
    area_missing_since = None
    try:
        if bool(config["ui"].get("pin_on_top", True)):
            toggle_pin()
        while True:
            loop_started = time.monotonic()
            if not window.hwnd and loop_started - last_search >= 1.0:
                window.find()
                last_search = loop_started
            frame = window.capture() if window.hwnd else None
            if frame is None:
                vision.reset_motion()
                last_area = None
                last_manual_area = None
                last_mode = None
                pending_mode_scan = False
                area_missing_since = None
                observation = Observation(0, 0, HandStatus.UNKNOWN, False)
                decision = controller.update(observation, loop_started)
                if window.hwnd and loop_started - last_search >= 1.0:
                    window.find()
                    last_search = loop_started
                    vision.reset_motion()
                blank = np.zeros((preview_h, preview_w, 3), dtype="uint8")
                display = draw_hud(blank, decision, observation, count, vision.zones,
                                   args.dry_run, preview_w, preview_h, pinned=pinned)
                cv2.putText(display, "Menunggu gambar kamera Libera...",
                            (20, 72 + preview_h // 2 - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
                cv2.putText(display, window.capture_status[:70],
                            (20, 72 + preview_h // 2 + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 180, 180), 1)
            else:
                mode = window.scan_mode
                if mode is not None and mode != last_mode:
                    pending_mode_scan = (mode in (ScanMode.ORIGINAL_IMAGE, ScanMode.BOOK,
                                                  ScanMode.SELECT_AREA) and last_mode is not None)
                    vision.reset_motion(reset_camera=False)
                    controller.reset_for_mode(loop_started)
                    last_area = None
                    last_manual_area = None
                    area_missing_since = None
                    last_mode = mode
                    if mode is not None:
                        print(f"[MODE] Libera: {mode.value}")
                area = area_for_mode(frame, mode, last_mode,
                                     selecting=mode == ScanMode.SELECT_AREA and window.selecting_area())
                if area is None:
                    if last_area is not None:
                        if area_missing_since is None:
                            area_missing_since = loop_started
                        elif loop_started - area_missing_since >= AREA_RECOVERY_SECONDS:
                            vision.reset_motion(reset_camera=False)
                            last_area = None
                            area_missing_since = None
                else:
                    area_missing_since = None
                    tolerance = (3 if mode == ScanMode.SELECT_AREA else
                                 max(8, round(max(frame.shape[:2]) * 0.01)))
                    if (last_area is not None and
                            np.max(np.abs(np.asarray(area.corners) -
                                          np.asarray(last_area.corners))) <= tolerance):
                        area = last_area
                    else:
                        if (mode == ScanMode.SELECT_AREA and
                                (last_manual_area is None or
                                 np.max(np.abs(np.asarray(area.corners) -
                                               np.asarray(last_manual_area.corners))) > tolerance)):
                            vision.reset_motion(reset_camera=False)
                            controller.reset_for_mode(loop_started)
                            pending_mode_scan = True
                            last_manual_area = area
                        last_area = area
                observation = vision.analyze(frame, loop_started, area)
                if pending_mode_scan and observation.area_valid and observation.frame_valid:
                    observation = Observation(
                        observation.motion_percent,
                        max(observation.scene_change_percent, controller.scene_threshold),
                        observation.hand)
                decision = controller.update(observation, loop_started)
                if decision.trigger:
                    sent = args.dry_run or window.trigger(config["trigger"])
                    if sent:
                        pending_mode_scan = False
                        count += 1
                        vision.accept_scene()
                        if config["ui"]["sound_feedback"] and not args.dry_run:
                            import winsound
                            winsound.Beep(1450, 120)
                        print(f"[SCAN] Perintah dikirim; total perintah: {count}")
                    else:
                        print("[WARN] Gagal mengirim perintah scan. Periksa fokus jendela Libera.")
                display = draw_hud(frame, decision, observation, count, vision.zones,
                                   args.dry_run, preview_w, preview_h, area,
                                   None if observation.frame_valid else vision.camera.reason,
                                   pinned)

            if decision.state != last_state:
                print(f"[STATUS] {decision.state.value}")
                last_state = decision.state
            cv2.imshow(hud_name, display)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("c"):
                calibrate_camera(window)
                vision.reset_motion()
                last_area = None
                last_manual_area = None
                last_mode = None
                pending_mode_scan = False
                area_missing_since = None
                controller.update(Observation(0, 0, HandStatus.UNKNOWN, False), time.monotonic())
            if key == ord("p"):
                controller.toggle_pause()
                vision.reset_motion()
            if key in (ord("t"), ord("T")):
                toggle_pin()
            if key == ord("s") and frame is not None and observation.frame_valid:
                sent = args.dry_run or window.trigger(config["trigger"])
                if sent:
                    count += 1
                    pending_mode_scan = False
                    if observation.area_valid:
                        vision.accept_scene()
                    else:
                        vision.reset_motion(reset_camera=False)
                        last_area = None
                        area_missing_since = None
                    controller.manual_trigger(time.monotonic())
                    print(f"[SCAN MANUAL] Perintah dikirim; total perintah: {count}")
                else:
                    print("[WARN] Gagal mengirim perintah scan manual")
            elif key == ord("s"):
                print("[WARN] Scan ditahan: gambar kamera belum siap")
            time.sleep(max(0, 0.04 - (time.monotonic() - loop_started)))
    except KeyboardInterrupt:
        pass
    finally:
        vision.close()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
