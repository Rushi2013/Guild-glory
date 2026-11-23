"""Android floating-overlay plumbing (SYSTEM_ALERT_WINDOW).

Three things have to happen for a real "display over other apps" bubble:

1. The manifest must request ``android.permission.SYSTEM_ALERT_WINDOW``
   (already declared in ``buildozer.spec`` - it is a special permission, so the
   user grants it from a Settings screen rather than a runtime dialog).
2. The app must send the user to that Settings screen if the grant is missing.
3. A *foreground service* must own the overlay window, because a plain Activity
   is paused as soon as another app comes forward.

All of the jnius calls are guarded, so importing this module on desktop is safe
and the panel can show a friendly "Android only" state instead of crashing.
"""

from __future__ import annotations

import sys
from typing import Optional

IS_ANDROID = sys.platform.startswith("android") or "ANDROID_ARGUMENT" in __import__(
    "os"
).environ

# p4a names the generated Java service class after the service entry point.
# If you rename the service in buildozer.spec, add the new class here.
SERVICE_CLASS_CANDIDATES = (
    "org.kivy.android.PythonService",
    "org.kivy.android.PythonServiceAuroraFloat",
)


class OverlayStatus:
    OK = "ok"
    NOT_ANDROID = "This build is not running on Android, so there is no overlay service."
    DENIED = "Overlay permission not granted - open Settings and allow 'Display over other apps'."
    ERROR = "Could not start the overlay service; check logcat for the Python traceback."


def _autoclass(name):
    from jnius import autoclass  # imported lazily: desktop has no jnius

    return autoclass(name)


def has_permission() -> bool:
    if not IS_ANDROID:
        return False
    try:
        from android import mActivity

        Settings = _autoclass("android.provider.Settings")
        return bool(Settings.canDrawOverlays(mActivity))
    except Exception:
        return False


def request_permission() -> bool:
    """Send the user to the 'Display over other apps' settings screen."""
    if not IS_ANDROID:
        return False
    try:
        from android import mActivity

        Intent = _autoclass("android.content.Intent")
        Settings = _autoclass("android.provider.Settings")
        Uri = _autoclass("android.net.Uri")
        intent = Intent(
            Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
            Uri.parse("package:" + mActivity.getPackageName()),
        )
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        mActivity.startActivity(intent)
        return True
    except Exception:
        return False


def start_service() -> Optional[str]:
    """Start the foreground overlay service.

    Returns ``None`` on success or a human-readable status string on failure.
    """
    if not IS_ANDROID:
        return OverlayStatus.NOT_ANDROID
    try:
        from android import mActivity

        last_error = None
        for candidate in SERVICE_CLASS_CANDIDATES:
            try:
                service_cls = _autoclass(candidate)
                service_cls.start(mActivity, "")
                return None
            except Exception as exc:  # wrong class name -> try the next one
                last_error = exc
        raise RuntimeError(last_error)
    except Exception:
        return OverlayStatus.ERROR


def ensure_overlay() -> Optional[str]:
    """One-call helper for the UI: permission check -> prompt -> start."""
    if not IS_ANDROID:
        return OverlayStatus.NOT_ANDROID
    if not has_permission():
        request_permission()
        return OverlayStatus.DENIED
    return start_service()
