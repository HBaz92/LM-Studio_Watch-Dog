from __future__ import annotations

import ctypes
import sys
from typing import Any


DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_SYSTEMBACKDROP_TYPE = 38

DWMWCP_ROUND = 2
DWMSBT_MAINWINDOW = 2


def apply_mica_to_hwnd(hwnd: int, dark: bool = False) -> bool:
    if sys.platform != "win32" or not hwnd:
        return False

    try:
        enabled = ctypes.c_int(1 if dark else 0)
        corner = ctypes.c_int(DWMWCP_ROUND)
        backdrop = ctypes.c_int(DWMSBT_MAINWINDOW)

        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(enabled),
            ctypes.sizeof(enabled),
        )
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(corner),
            ctypes.sizeof(corner),
        )
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(backdrop),
            ctypes.sizeof(backdrop),
        )
        return result == 0
    except Exception:
        return False


def apply_mica_window(window: Any, dark: bool = False) -> bool:
    try:
        if hasattr(window, "update_idletasks"):
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
            return apply_mica_to_hwnd(int(hwnd), dark=dark)

        if hasattr(window, "winId"):
            return apply_mica_to_hwnd(int(window.winId()), dark=dark)
    except Exception:
        return False

    return False
