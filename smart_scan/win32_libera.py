from __future__ import annotations

import ctypes
import time
from contextlib import contextmanager
from ctypes import wintypes

import numpy as np

from .scan_mode import ScanMode, detect_scan_mode
from .viewport import find_camera_rect


user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p


@contextmanager
def physical_pixels():
    """Keep window geometry and PrintWindow bitmap sizes in physical pixels."""
    previous = user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    if not previous:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        user32.SetThreadDpiAwarenessContext(previous)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
user32.PrintWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.keybd_event.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, wintypes.DWORD, ctypes.POINTER(ctypes.c_ulong)]
user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_ulong)]
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
                           ctypes.c_void_p, ctypes.POINTER(BITMAPINFO), wintypes.UINT]
gdi32.GetDIBits.restype = ctypes.c_int
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wintypes.HDC]


class LiberaWindow:
    def __init__(self, config: dict):
        self.config = config
        self.hwnd: int | None = None
        self.rect: tuple[int, int, int, int] | None = None
        self.camera_rect: tuple[int, int, int, int] | None = None
        self.camera_window_size: tuple[int, int] | None = None
        self.camera_checked_at = 0.0
        self.capture_status = "Jendela Libera belum ditemukan"
        self.last_window_frame: np.ndarray | None = None
        self.scan_mode: ScanMode | None = None
        self.manual_camera_rect: tuple[int, int, int, int] | None = None
        self.manual_window_size: tuple[int, int] | None = None

    def selecting_area(self) -> bool:
        return bool(user32.GetAsyncKeyState(0x01) & 0x8000)

    @physical_pixels()
    def find(self) -> bool:
        matches = []
        wanted_title = self.config["title_contains"].lower()
        wanted_class = self.config["class_name"]

        def visit(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            title = ctypes.create_unicode_buffer(256)
            cls = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, 256)
            user32.GetClassNameW(hwnd, cls, 256)
            if wanted_title not in title.value.lower() or cls.value != wanted_class:
                return True
            rect = wintypes.RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                width = rect.right - rect.left
                height = rect.bottom - rect.top
                if width > 600 and height > 400:
                    matches.append((width * height, hwnd))
            return True

        callback = WNDENUMPROC(visit)
        user32.EnumWindows(callback, 0)
        new_hwnd = max(matches)[1] if matches else None
        if new_hwnd != self.hwnd:
            self.camera_rect = None
            self.camera_window_size = None
            self.manual_camera_rect = None
            self.manual_window_size = None
            self.capture_status = ("Mengambil gambar Libera" if new_hwnd else
                                   "Jendela Libera tidak ditemukan: periksa judul dan kelas jendela")
        self.hwnd = new_hwnd
        return self.hwnd is not None

    @physical_pixels()
    def capture(self) -> np.ndarray | None:
        self.last_window_frame = None
        self.scan_mode = None
        hwnd = self.hwnd
        if not hwnd or not user32.IsWindow(hwnd) or user32.IsIconic(hwnd):
            self.capture_status = "Jendela Libera tertutup atau diminimalkan"
            return None
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            self.capture_status = "Ukuran jendela Libera tidak terbaca"
            return None
        w, h = rect.right - rect.left, rect.bottom - rect.top
        if w < 100 or h < 100:
            self.capture_status = "Jendela Libera terlalu kecil"
            return None
        self.rect = (rect.left, rect.top, w, h)
        screen = user32.GetDC(hwnd)
        if not screen:
            self.capture_status = "Gagal mengakses gambar jendela Libera"
            return None
        memory = None
        bitmap = None
        old = None
        try:
            memory = gdi32.CreateCompatibleDC(screen)
            bitmap = gdi32.CreateCompatibleBitmap(screen, w, h)
            if not memory or not bitmap:
                self.capture_status = "Gagal menyiapkan penangkapan jendela"
                return None
            old = gdi32.SelectObject(memory, bitmap)
            if not old or not user32.PrintWindow(hwnd, memory, 2):
                self.capture_status = "Libera tidak merespons permintaan gambar (PrintWindow)"
                return None
            gdi32.SelectObject(memory, old)
            old = None
            info = BITMAPINFO()
            info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            info.bmiHeader.biWidth = w
            info.bmiHeader.biHeight = -h
            info.bmiHeader.biPlanes = 1
            info.bmiHeader.biBitCount = 32
            buf = ctypes.create_string_buffer(w * h * 4)
            if gdi32.GetDIBits(memory, bitmap, 0, h, buf, ctypes.byref(info), 0) != h:
                self.capture_status = "Gambar jendela Libera tidak terbaca"
                return None
            bgr = np.frombuffer(buf, np.uint8).reshape(h, w, 4)[:, :, :3]
            self.last_window_frame = bgr.copy()
            if self.manual_window_size != (w, h):
                self.manual_camera_rect = None
                self.manual_window_size = None
            now = time.monotonic()
            if (self.camera_window_size != (w, h) or
                    now - self.camera_checked_at >= 0.5):
                self.camera_rect = find_camera_rect(bgr, self.config["camera_layout"])
                self.camera_window_size = (w, h)
                self.camera_checked_at = now
            camera = self.manual_camera_rect or self.camera_rect
            if camera is None:
                self.capture_status = f"Bidang kamera tidak dikenali (jendela {w}x{h})"
                return None
            x1, y1, x2, y2 = camera
            crop = bgr[y1:y2, x1:x2]
            if not crop.size:
                self.capture_status = "Bidang kamera kosong"
                return None
            self.scan_mode = detect_scan_mode(bgr, camera)
            self.capture_status = "OK"
            return crop.copy()
        finally:
            if old:
                gdi32.SelectObject(memory, old)
            if bitmap:
                gdi32.DeleteObject(bitmap)
            if memory:
                gdi32.DeleteDC(memory)
            user32.ReleaseDC(hwnd, screen)

    @physical_pixels()
    def trigger(self, config: dict) -> bool:
        hwnd = self.hwnd
        if not hwnd or not user32.IsWindow(hwnd) or not self.rect:
            return False
        user32.ShowWindow(hwnd, 9)
        if not user32.SetForegroundWindow(hwnd):
            return False
        method = config["method"]
        if method == "hotkey":
            code = {"F12": 0x7B, "SPACE": 0x20}.get(config["hotkey"].upper())
            if code is None:
                raise ValueError("Hotkey yang didukung: F12 atau SPACE")
            user32.keybd_event(code, 0, 0, None)
            user32.keybd_event(code, 0, 2, None)
            return True
        if method == "click":
            x, y, w, h = self.rect
            px, py = config["click_position"]
            old = wintypes.POINT()
            if not user32.GetCursorPos(ctypes.byref(old)):
                return False
            if not user32.SetCursorPos(x + int(w * px), y + int(h * py)):
                return False
            try:
                user32.mouse_event(2, 0, 0, 0, None)
                user32.mouse_event(4, 0, 0, 0, None)
            finally:
                user32.SetCursorPos(old.x, old.y)
            return True
        raise ValueError("trigger.method harus hotkey atau click")
