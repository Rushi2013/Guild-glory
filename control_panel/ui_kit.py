"""
ui_kit.py - a small, dependency-free widget kit that makes Tkinter look modern.

Everything here uses only the Python standard library (`tkinter`). No Pillow,
no custom ttk themes, no image assets. Rounded shapes are painted on Canvas
widgets - the standard trick for getting rounded, "designed" surfaces without
shipping PNGs, and it keeps the whole thing resolution independent.

Widgets
-------
round_rect()      helper  - draws a rounded rectangle on any Canvas
Card              surface - rounded panel that auto-sizes to the widgets in .body
RoundedButton     button  - filled / ghost / subtle / danger with hover + press
ToggleSwitch      switch  - animated on/off control
Slider            slider  - draggable track with a filled progress portion
Chip              label   - small rounded status pill
Divider           rule    - 1px hairline in the border colour
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

# --------------------------------------------------------------------------- #
# Palette - one place to re-skin the whole application
# --------------------------------------------------------------------------- #
COLORS = {
    "bg":        "#0b0e14",   # window background
    "bg_alt":    "#0e121b",   # sidebar / rails
    "card":      "#141a26",   # raised surfaces
    "card_soft": "#0f1521",   # inset surfaces (log, tracks)
    "card_hi":   "#1b2333",   # hovered surface
    "nav_hover": "#151c29",
    "border":    "#22293a",
    "text":      "#e6edf3",
    "muted":     "#8b97ad",
    "accent":    "#7c5cff",
    "accent_hi": "#9a80ff",
    "cyan":      "#35d6e8",
    "ok":        "#3fb950",
    "warn":      "#e3b341",
    "danger":    "#f85149",
}

BUTTON_STYLES = {
    "primary": {"fill": COLORS["accent"], "hover": COLORS["accent_hi"],
                "press": "#6a4bdd", "fg": "#ffffff", "outline": ""},
    "ghost":   {"fill": None, "hover": COLORS["card_hi"], "press": "#232c40",
                "fg": COLORS["text"], "outline": COLORS["border"]},
    "subtle":  {"fill": COLORS["card_hi"], "hover": "#232c40", "press": "#2b3549",
                "fg": "#cfd8e6", "outline": ""},
    "danger":  {"fill": "#3a1d22", "hover": "#4a252b", "press": "#5a2d34",
                "fg": "#ff8f88", "outline": "#5a2d34"},
}

# --------------------------------------------------------------------------- #
# Fonts - resolved once against what the OS actually has installed
# --------------------------------------------------------------------------- #
_UI_FAMILY = "TkDefaultFont"
_MONO_FAMILY = "TkFixedFont"


def init_fonts(root: tk.Misc) -> None:
    """Pick the nicest UI + monospace font available on this machine."""
    global _UI_FAMILY, _MONO_FAMILY
    try:
        families = {name.lower() for name in tkfont.families(root)}
    except tk.TclError:  # pragma: no cover - headless / no font system
        return

    for name in ("Segoe UI Variable Text", "Segoe UI", "Inter", "SF Pro Text",
                 "Helvetica Neue", "Ubuntu", "Noto Sans", "DejaVu Sans", "Arial"):
        if name.lower() in families:
            _UI_FAMILY = name
            break

    for name in ("Cascadia Mono", "Consolas", "SF Mono", "Menlo", "Ubuntu Mono",
                 "DejaVu Sans Mono", "Courier New"):
        if name.lower() in families:
            _MONO_FAMILY = name
            break


def UI(size: int = 11, weight: str = "normal"):
    """Return a Tk font spec for the UI family."""
    return (_UI_FAMILY, size) if weight == "normal" else (_UI_FAMILY, size, weight)


def MONO(size: int = 9, weight: str = "normal"):
    """Return a Tk font spec for the monospace family."""
    return (_MONO_FAMILY, size) if weight == "normal" else (_MONO_FAMILY, size, weight)


def _make_font(widget: tk.Misc, spec) -> tkfont.Font:
    """Build a measurable Font object from a (family, size[, weight]) tuple."""
    try:
        family = spec[0]
        size = spec[1]
        weight = spec[2] if len(spec) > 2 else "normal"
        return tkfont.Font(root=widget, family=family, size=size, weight=weight)
    except (tk.TclError, IndexError, TypeError):
        try:
            return tkfont.Font(root=widget, size=10)
        except tk.TclError:  # pragma: no cover - very unusual font system
            return tkfont.Font(size=10)


def _bg_of(widget: tk.Misc) -> str:
    """Best-effort read of a parent's background colour."""
    try:
        return str(widget.cget("bg"))
    except Exception:
        return COLORS["bg"]


# --------------------------------------------------------------------------- #
# Primitive: rounded rectangle
# --------------------------------------------------------------------------- #
def round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r, **kwargs):
    """
    Draw a rounded rectangle as a smoothed polygon.

    Tk has no native rounded-rect item, but `create_polygon(..., smooth=True)`
    interpolates the corner points into arcs. The point list below deliberately
    duplicates each corner point (corner, corner, corner+radius) so the spline
    flattens out along the edges and only curves at the corners.
    """
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1,
        x2, y1 + r, x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2, x1, y2,
        x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


# --------------------------------------------------------------------------- #
# Card
# --------------------------------------------------------------------------- #
class Card(tk.Frame):
    """
    A rounded panel. Put your widgets in `.body`.

    Sizing model:
      * width  -> whatever the geometry manager gives the card (pack fill="x")
      * height -> driven by the *content*: whenever `.body` changes its
                  requested height the card re-sizes itself, so you never have
                  to hard-code pixel heights.
    The rounded background is painted on a Canvas that sits *behind* `.body`,
    and `.body` is inset by `padding`, so its square corners never poke out of
    the rounded outline.
    """

    def __init__(self, master, radius: int = 16, padding: int = 18,
                 fill: str | None = None, outline: str | None = None,
                 parent_bg: str | None = None, **kwargs):
        parent_bg = parent_bg or _bg_of(master)
        super().__init__(master, bg=parent_bg, highlightthickness=0, bd=0, **kwargs)

        self._radius = radius
        self._padding = padding
        self._fill = fill or COLORS["card"]
        self._outline = outline or COLORS["border"]
        self._parent_bg = parent_bg
        self._last_body_h = 0

        self.canvas = tk.Canvas(self, bg=parent_bg, highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self.body = tk.Frame(self, bg=self._fill)
        self.body.place(x=padding, y=padding)

        self.bind("<Configure>", self._on_resize)
        self.body.bind("<Configure>", self._on_body_resize)

    def _on_resize(self, event):
        self._paint(event.width, event.height)
        self.body.place_configure(width=max(1, event.width - 2 * self._padding))

    def _on_body_resize(self, event):
        if event.height != self._last_body_h:
            self._last_body_h = event.height
            self.configure(height=event.height + 2 * self._padding)

    def _paint(self, w: int, h: int) -> None:
        self.canvas.delete("all")
        if w < 6 or h < 6:
            return
        round_rect(self.canvas, 1, 1, w - 1, h - 1, self._radius,
                   fill=self._fill, outline=self._outline, width=1)


# --------------------------------------------------------------------------- #
# Button
# --------------------------------------------------------------------------- #
class RoundedButton(tk.Canvas):
    """Canvas-painted button with hover / press states and several variants."""

    def __init__(self, master, text: str, command=None, variant: str = "primary",
                 width: int = 150, height: int = 40, radius: int = 12,
                 font=None, parent_bg: str | None = None):
        self._parent_bg = parent_bg or _bg_of(master)
        super().__init__(master, width=width, height=height, bg=self._parent_bg,
                         highlightthickness=0, bd=0, cursor="hand2")

        self._text = text
        self._font = font or UI(10, "bold")
        self._radius = radius
        self._command = command
        self._spec = dict(BUTTON_STYLES.get(variant, BUTTON_STYLES["primary"]))
        self._state = "normal"   # normal | hover | press
        self._enabled = True

        self._draw()
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    # -- public API ---------------------------------------------------------
    def set_text(self, text: str) -> None:
        self._text = text
        self._draw()

    def set_variant(self, variant: str) -> None:
        self._spec = dict(BUTTON_STYLES.get(variant, BUTTON_STYLES["primary"]))
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        self.configure(cursor="hand2" if enabled else "arrow")
        self._state = "normal"
        self._draw()

    # -- painting -----------------------------------------------------------
    def _current_fill(self):
        if not self._enabled:
            return COLORS["card_soft"]
        key = {"normal": "fill", "hover": "hover", "press": "press"}[self._state]
        return self._spec[key]

    def _draw(self) -> None:
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1:
            w = int(self["width"])
        if h <= 1:
            h = int(self["height"])
        if w < 4 or h < 4:
            return

        fill = self._current_fill() or self._parent_bg
        outline = self._spec["outline"] if self._enabled else ""
        round_rect(self, 0.5, 0.5, w - 0.5, h - 0.5, self._radius,
                   fill=fill, outline=outline or fill, width=1)

        fg = self._spec["fg"] if self._enabled else COLORS["muted"]
        self.create_text(w / 2, h / 2 + 1, text=self._text, fill=fg,
                         font=self._font, anchor="center")

        # 1px accent lift on the top edge of filled buttons reads as depth
        if self._enabled and self._spec["fill"] and self._state != "press":
            self.create_line(self._radius, 1.5, w - self._radius, 1.5,
                             fill="#ffffff", stipple="gray12", width=1)

    # -- events -------------------------------------------------------------
    def _on_enter(self, _event=None):
        if not self._enabled:
            return
        self._state = "hover"
        self._draw()

    def _on_leave(self, _event=None):
        if not self._enabled:
            return
        self._state = "normal"
        self._draw()

    def _on_press(self, _event=None):
        if not self._enabled:
            return
        self._state = "press"
        self._draw()

    def _on_release(self, event=None):
        if not self._enabled:
            return
        inside = (event is not None and 0 <= event.x <= self.winfo_width()
                  and 0 <= event.y <= self.winfo_height())
        self._state = "hover" if inside else "normal"
        self._draw()
        if inside and self._command is not None:
            self._command()


# --------------------------------------------------------------------------- #
# Toggle switch
# --------------------------------------------------------------------------- #
class ToggleSwitch(tk.Canvas):
    """
    Animated iOS-style switch.

    The knob position is a float `_t` in [0, 1]; each animation frame nudges it
    toward the target and repaints. That is what makes it feel physical instead
    of snapping.
    """

    def __init__(self, master, value: bool = False, command=None,
                 width: int = 54, height: int = 30, parent_bg: str | None = None):
        parent_bg = parent_bg or _bg_of(master)
        super().__init__(master, width=width, height=height, bg=parent_bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._w, self._h = width, height
        self._value = bool(value)
        self._t = 1.0 if self._value else 0.0
        self._command = command
        self._anim = None

        self._draw()
        self.bind("<Button-1>", self._on_click)

    # -- public API ---------------------------------------------------------
    def get(self) -> bool:
        return self._value

    def set_value(self, value: bool, notify: bool = False) -> None:
        value = bool(value)
        if value == self._value:
            return
        self._value = value
        self._start_animation()
        if notify and self._command is not None:
            self._command(self._value)

    # -- painting -----------------------------------------------------------
    def _draw(self) -> None:
        self.delete("all")
        w, h = self._w, self._h
        pad = 3
        r = h / 2
        track_on, track_off = COLORS["accent"], "#2a3346"
        track = track_on if self._t > 0.5 else track_off
        round_rect(self, 0.5, 0.5, w - 0.5, h - 0.5, r, fill=track, outline=track)

        knob_d = h - 2 * pad
        travel = (w - 2 * pad) - knob_d
        cx = pad + knob_d / 2 + travel * self._t
        self.create_oval(cx - knob_d / 2, pad, cx + knob_d / 2, pad + knob_d,
                         fill="#ffffff", outline="")

    # -- animation ----------------------------------------------------------
    def _start_animation(self) -> None:
        if self._anim is not None:
            try:
                self.after_cancel(self._anim)
            except tk.TclError:
                pass
            self._anim = None
        self._animate()

    def _animate(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return

        target = 1.0 if self._value else 0.0
        step = 0.18
        if abs(self._t - target) <= step:
            self._t = target
            self._draw()
            self._anim = None
            return

        self._t += step if target > self._t else -step
        self._draw()
        self._anim = self.after(12, self._animate)

    # -- events -------------------------------------------------------------
    def _on_click(self, _event=None):
        self._value = not self._value
        self._start_animation()
        if self._command is not None:
            self._command(self._value)


# --------------------------------------------------------------------------- #
# Slider
# --------------------------------------------------------------------------- #
class Slider(tk.Canvas):
    """A draggable track. Values are snapped to `step` and clamped."""

    def __init__(self, master, minimum: float = 0, maximum: float = 100,
                 value: float | None = None, step: float = 1, command=None,
                 width: int = 240, height: int = 30, parent_bg: str | None = None):
        parent_bg = parent_bg or _bg_of(master)
        super().__init__(master, width=width, height=height, bg=parent_bg,
                         highlightthickness=0, bd=0, cursor="hand2")

        self._min = float(minimum)
        self._max = float(maximum) if maximum > minimum else float(minimum + 1)
        self._step = max(float(step), 0.0)
        self._value = self._clamp(float(value if value is not None else minimum))
        self._command = command
        self._pad = 10

        self._draw()
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Button-1>", self._on_event)
        self.bind("<B1-Motion>", self._on_event)
        self.bind("<ButtonRelease-1>", lambda _e: self._draw())

    # -- value helpers ------------------------------------------------------
    def _clamp(self, value: float) -> float:
        value = max(self._min, min(self._max, value))
        if self._step > 0:
            steps = round((value - self._min) / self._step)
            value = self._min + steps * self._step
            value = max(self._min, min(self._max, value))
        return value

    def get(self) -> float:
        return self._value

    def set(self, value: float, notify: bool = False) -> None:
        value = self._clamp(float(value))
        if value == self._value:
            return
        self._value = value
        self._draw()
        if notify and self._command is not None:
            self._command(self._value)

    def _ratio(self) -> float:
        return (self._value - self._min) / (self._max - self._min)

    def _x_for(self, value: float) -> float:
        w = self.winfo_width() if self.winfo_width() > 1 else int(self["width"])
        usable = max(1, w - 2 * self._pad)
        ratio = (value - self._min) / (self._max - self._min)
        return self._pad + usable * ratio

    def _value_for(self, x: float) -> float:
        w = self.winfo_width() if self.winfo_width() > 1 else int(self["width"])
        usable = max(1, w - 2 * self._pad)
        ratio = (x - self._pad) / usable
        return self._min + max(0.0, min(1.0, ratio)) * (self._max - self._min)

    # -- painting -----------------------------------------------------------
    def _draw(self) -> None:
        self.delete("all")
        w = self.winfo_width() if self.winfo_width() > 1 else int(self["width"])
        h = self.winfo_height() if self.winfo_height() > 1 else int(self["height"])
        if w < 10 or h < 10:
            return

        cy = h / 2
        x_end = w - self._pad
        knob_x = self._x_for(self._value)

        self.create_line(self._pad, cy, x_end, cy, fill="#242c3d",
                         width=6, capstyle="round")
        if knob_x > self._pad + 1:
            self.create_line(self._pad, cy, knob_x, cy, fill=COLORS["accent"],
                             width=6, capstyle="round")
        self.create_oval(knob_x - 7, cy - 7, knob_x + 7, cy + 7,
                         fill="#ffffff", outline=COLORS["accent"], width=2)

    # -- events -------------------------------------------------------------
    def _on_event(self, event):
        value = self._clamp(self._value_for(event.x))
        if value != self._value:
            self._value = value
            self._draw()
            if self._command is not None:
                self._command(self._value)


# --------------------------------------------------------------------------- #
# Chip + Divider
# --------------------------------------------------------------------------- #
class Chip(tk.Canvas):
    """Small rounded status pill. Width follows the text automatically."""

    def __init__(self, master, text: str, fg: str = COLORS["ok"],
                 parent_bg: str | None = None, font=None,
                 padx: int = 12, height: int = 26):
        self._parent_bg = parent_bg or _bg_of(master)
        self._font_spec = font or UI(9, "bold")
        self._padx = padx
        self._h = height
        self._text = text
        self._fg = fg
        super().__init__(master, width=100, height=height, bg=self._parent_bg,
                         highlightthickness=0, bd=0)
        self._fnt = _make_font(self, self._font_spec)
        self._draw()

    def _measure(self, text: str) -> int:
        try:
            width = self._fnt.measure(text)
        except tk.TclError:
            width = len(text) * 7
        return int(width + 2 * self._padx)

    def set_text(self, text: str, fg: str | None = None, bg: str | None = None) -> None:
        self._text = text
        if fg:
            self._fg = fg
        if bg:
            self.configure(bg=bg)
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w = max(self._measure(self._text), 36)
        self.configure(width=w)
        round_rect(self, 0.5, 0.5, w - 0.5, self._h - 0.5, (self._h - 1) / 2,
                   fill=COLORS["card_soft"], outline=self._fg, width=1)
        self.create_text(w / 2, self._h / 2 + 1, text=self._text,
                         fill=self._fg, font=self._fnt, anchor="center")


class Divider(tk.Frame):
    """1px hairline."""

    def __init__(self, master, color: str = COLORS["border"], **kwargs):
        super().__init__(master, bg=color, height=1, highlightthickness=0,
                         bd=0, **kwargs)
