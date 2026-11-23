"""Aurora floating bubble - python-for-android foreground service.

Started by the panel's FLOAT button (``aurora.android_overlay.start_service``).

It owns a ``TYPE_APPLICATION_OVERLAY`` window: a 56dp circular bubble that can be
dragged anywhere on screen and taps back into the panel activity. This is the
same mechanism chat-head apps use, and it is the only piece of the build that has
to run on a real device to be verified.

On-device checklist
-------------------
1. Panel -> FLOAT -> Android opens "Display over other apps" for this app.
2. Grant it, come back, tap FLOAT again.
3. ``adb logcat | grep python`` should show ``[aurora] bubble added``.
4. Press home: the bubble stays above the launcher.
"""

from __future__ import annotations

import time

from jnius import PythonJavaClass, autoclass, java_method

# -- Android plumbing --------------------------------------------------------
PythonService = autoclass("org.kivy.android.PythonService")
service = PythonService.mService

Context = autoclass("android.content.Context")
WindowManager = autoclass("android.view.WindowManager")
LayoutParams = autoclass("android.view.WindowManager$LayoutParams")
Gravity = autoclass("android.view.Gravity")
PixelFormat = autoclass("android.graphics.PixelFormat")
GradientDrawable = autoclass("android.graphics.drawable.GradientDrawable")
TextView = autoclass("android.widget.TextView")
MotionEvent = autoclass("android.view.MotionEvent")
BuildVersion = autoclass("android.os.Build$VERSION")

DENSITY = service.getResources().getDisplayMetrics().density


def dp(value: float) -> int:
    return int(value * DENSITY + 0.5)


def argb(a: int, r: int, g: int, b: int) -> int:
    """Java ints are signed - pack ARGB and fold into 32-bit signed range."""
    packed = (a << 24) | (r << 16) | (g << 8) | b
    return packed - (1 << 32) if packed >= (1 << 31) else packed


CYAN = argb(255, 56, 204, 255)
VIOLET = argb(255, 139, 113, 255)
GLASS = argb(235, 12, 18, 34)


# -- bubble ------------------------------------------------------------------
class Bubble:
    def __init__(self) -> None:
        self.wm = service.getSystemService(Context.WINDOW_SERVICE)
        self.view = self._build_view()
        self.params = self._build_params()
        self.view.setOnTouchListener(_TouchHandler(self))

    def _build_view(self):
        view = TextView(service)
        view.setText("A")
        view.setTextSize(17)
        view.setTextColor(CYAN)
        view.setGravity(Gravity.CENTER)
        view.setTypeface(None, 1)  # bold

        bg = GradientDrawable()
        bg.setShape(GradientDrawable.OVAL)
        bg.setColor(GLASS)
        bg.setStroke(dp(2), CYAN)
        view.setBackground(bg)
        return view

    def _build_params(self):
        if BuildVersion.SDK_INT >= 26:
            window_type = LayoutParams.TYPE_APPLICATION_OVERLAY
        else:
            window_type = LayoutParams.TYPE_PHONE
        flags = (
            LayoutParams.FLAG_NOT_FOCUSABLE
            | LayoutParams.FLAG_LAYOUT_NO_LIMITS
            | LayoutParams.FLAG_LAYOUT_IN_SCREEN
        )
        params = LayoutParams(
            dp(56), dp(56), window_type, flags, PixelFormat.TRANSLUCENT
        )
        params.gravity = Gravity.TOP | Gravity.START
        params.x = dp(12)
        params.y = dp(140)
        return params

    def show(self) -> None:
        self.wm.addView(self.view, self.params)
        print("[aurora] bubble added")

    def move_to(self, x: int, y: int) -> None:
        self.params.x = int(x)
        self.params.y = int(y)
        self.wm.updateViewLayout(self.view, self.params)

    def destroy(self) -> None:
        try:
            self.wm.removeView(self.view)
        except Exception:
            pass


class _TouchHandler(PythonJavaClass):
    __javainterfaces__ = ["android/view/View$OnTouchListener"]
    __javacontext__ = "app"

    def __init__(self, bubble: Bubble) -> None:
        super().__init__()
        self.bubble = bubble
        self.start_x = 0
        self.start_y = 0
        self.touch_x = 0.0
        self.touch_y = 0.0
        self.moved = False

    @java_method("(Landroid/view/View;Landroid/view/MotionEvent;)Z")
    def onTouch(self, _view, event):
        action = event.getAction()
        if action == MotionEvent.ACTION_DOWN:
            self.start_x = self.bubble.params.x
            self.start_y = self.bubble.params.y
            self.touch_x = event.getRawX()
            self.touch_y = event.getRawY()
            self.moved = False
        elif action == MotionEvent.ACTION_MOVE:
            dx = event.getRawX() - self.touch_x
            dy = event.getRawY() - self.touch_y
            if abs(dx) > dp(6) or abs(dy) > dp(6):
                self.moved = True
            self.bubble.move_to(self.start_x + dx, self.start_y + dy)
        elif action == MotionEvent.ACTION_UP:
            if not self.moved:
                open_panel()
        return True


def open_panel() -> None:
    """Bring the panel activity to the front (avoids duplicating the task)."""
    Intent = autoclass("android.content.Intent")
    try:
        launch = service.getPackageManager().getLaunchIntentForPackage(
            service.getPackageName()
        )
        if launch is not None:
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP)
            service.startActivity(launch)
    except Exception as exc:  # pragma: no cover - device only
        print(f"[aurora] open_panel failed: {exc}")


# -- lifecycle ---------------------------------------------------------------
bubble: Bubble | None = None


def start(_args=None) -> None:
    """Entry point p4a calls for this service."""
    global bubble
    try:
        bubble = Bubble()
        # Views must be attached on the UI thread.
        try:
            from android.runnable import run_on_ui_thread

            run_on_ui_thread(bubble.show)()
        except Exception:
            bubble.show()
    except Exception as exc:  # pragma: no cover - device only
        print(f"[aurora] overlay failed: {exc}")

    print("[aurora] service running")
    while True:
        time.sleep(1.0)


start()
