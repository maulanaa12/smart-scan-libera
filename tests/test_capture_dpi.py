import ctypes
import sys
import unittest
from unittest.mock import MagicMock, patch

import numpy as np


@unittest.skipUnless(sys.platform == "win32", "Windows capture")
class CaptureDpiTests(unittest.TestCase):
    def setUp(self):
        from smart_scan import win32_libera
        self.module = win32_libera
        self.context = 1
        self.user = MagicMock()
        self.gdi = MagicMock()

        def set_context(value):
            old = self.context
            self.context = value.value if isinstance(value, ctypes.c_void_p) else value
            return old

        def get_rect(hwnd, pointer):
            rect = pointer._obj
            rect.left, rect.top = -200, 40
            # A 125% desktop returns a smaller rectangle to an unaware caller.
            width, height = (1320, 880) if self.context == ctypes.c_void_p(-4).value else (1056, 704)
            rect.right, rect.bottom = rect.left + width, rect.top + height
            return 1

        self.raw = np.zeros((880, 1320, 4), dtype=np.uint8)
        self.raw[804, 1059, :3] = (40, 180, 230)

        def read_pixels(dc, bitmap, start, height, buf, info, mode):
            header = info._obj.bmiHeader
            self.assertEqual((header.biWidth, -header.biHeight), (1320, 880))
            ctypes.memmove(buf, self.raw.ctypes.data, self.raw.nbytes)
            return height

        self.user.SetThreadDpiAwarenessContext.side_effect = set_context
        self.user.GetWindowRect.side_effect = get_rect
        self.user.IsIconic.return_value = False
        self.gdi.GetDIBits.side_effect = read_pixels
        self.window = self.module.LiberaWindow({"camera_layout": {}})
        self.window.hwnd = 123

    def test_full_bitmap_uses_physical_size_and_restores_context(self):
        with patch.object(self.module, "user32", self.user), patch.object(self.module, "gdi32", self.gdi), \
                patch.object(self.module, "find_camera_rect", return_value=(180, 145, 1060, 805)):
            frame = self.window.capture()
        self.assertEqual(frame.shape, (660, 880, 3))
        np.testing.assert_array_equal(frame[-1, -1], (40, 180, 230))
        self.gdi.CreateCompatibleBitmap.assert_called_once_with(self.user.GetDC.return_value, 1320, 880)
        self.assertEqual(self.context, 1)

    def test_capture_failure_restores_dpi_context(self):
        self.user.PrintWindow.return_value = False
        with patch.object(self.module, "user32", self.user), patch.object(self.module, "gdi32", self.gdi):
            self.assertIsNone(self.window.capture())
        self.assertEqual(self.context, 1)

    def test_manual_camera_selection_works_when_detection_fails(self):
        self.window.manual_window_size = (1320, 880)
        self.window.manual_camera_rect = (180, 145, 1060, 805)
        with patch.object(self.module, "user32", self.user), patch.object(self.module, "gdi32", self.gdi), \
                patch.object(self.module, "find_camera_rect", return_value=None):
            frame = self.window.capture()
        self.assertEqual(frame.shape, (660, 880, 3))
        np.testing.assert_array_equal(frame[-1, -1], (40, 180, 230))


if __name__ == "__main__":
    unittest.main()
