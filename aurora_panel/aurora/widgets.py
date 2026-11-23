"""Hand-drawn Kivy widgets that make the panel look like a product, not a form.

Everything here is vector canvas drawing (``RoundedRectangle`` / ``Ellipse`` /
``Line``) so it stays crisp on any DPI without shipping image assets.
"""

from __future__ import annotations

from typing import Callable, Optional

from kivy.animation import Animation
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from . import theme


# ---------------------------------------------------------------- primitives
class AuroraCard(BoxLayout):
    """Rounded, hairline-bordered container with an uppercase section header."""

    title = StringProperty("")

    def __init__(self, title: str = "", accent=theme.ACCENT,
                 fixed_height: Optional[float] = None, **kwargs):
        super().__init__(
            orientation="vertical",
            padding=[dp(14), dp(12), dp(14), dp(14)],
            spacing=dp(10),
            size_hint_y=None,
            **kwargs,
        )
        self.title = title
        self.accent = accent
        with self.canvas.before:
            self._fill_color = Color(*theme.CARD)
            self._fill = RoundedRectangle(radius=[dp(16)])
            self._border_color = Color(*theme.BORDER)
            self._border = Line(rounded_rectangle=(0, 0, 0, 0, dp(16)), width=1.0)
            self._bar_color = Color(*accent)
            self._bar = RoundedRectangle(radius=[dp(2)], size=(dp(22), dp(3)))

        if title:
            self.add_widget(self._make_header(title))

        self.bind(
            pos=self._relayout,
            size=self._relayout,
            height=self._relayout,
        )
        if fixed_height:
            self.height = fixed_height
        else:
            self.bind(minimum_height=self.setter("height"))

    def _make_header(self, title: str) -> BoxLayout:
        row = BoxLayout(size_hint_y=None, height=dp(20), spacing=dp(8))
        label = Label(
            text=title.upper(),
            color=theme.TEXT_DIM,
            font_size=sp(11),
            bold=True,
            halign="left",
            valign="middle",
        )
        label.bind(size=lambda w, *_: setattr(w, "text_size", (w.width, None)))
        row.add_widget(label)
        return row

    def _relayout(self, *_):
        self._fill.pos = self.pos
        self._fill.size = self.size
        self._border.rounded_rectangle = (
            self.x,
            self.y,
            self.width,
            self.height,
            dp(16),
        )
        # accent tick sits just above the first child
        self._bar.pos = (self.x + dp(14), self.top - dp(7))


class AuroraSwitch(Widget):
    """Pill switch with an animated knob."""

    active = BooleanProperty(False)
    progress = NumericProperty(0.0)

    def __init__(self, active: bool = False, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(50), dp(28)))
        super().__init__(**kwargs)
        with self.canvas:
            self._track_color = Color(*theme.TRACK)
            self._track = RoundedRectangle(radius=[dp(14)])
            self._knob_color = Color(0.72, 0.76, 0.84, 1)
            self._knob = Ellipse()
        self.bind(pos=self._sync, size=self._sync, progress=self._sync)
        self.active = active
        self.progress = 1.0 if active else 0.0
        self._sync()

    def on_active(self, _instance, value):
        Animation(progress=1.0 if value else 0.0, d=0.14, t="out_quad").start(self)

    def _sync(self, *_):
        w, h = self.size
        pad = dp(3)
        knob = h - pad * 2
        travel = max(0.0, w - pad * 2 - knob)
        self._track.pos = self.pos
        self._track.size = self.size
        self._track.radius = [h / 2.0]
        self._knob.pos = (self.x + pad + travel * self.progress, self.y + pad)
        self._knob.size = (knob, knob)
        self._track_color.rgba = theme.mix(theme.TRACK, theme.ACCENT, self.progress)
        self._knob_color.rgba = theme.mix(
            (0.72, 0.76, 0.84, 1), theme.BG_DEEP, self.progress
        )

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.active = not self.active
            return True
        return super().on_touch_down(touch)


class ToggleRow(BoxLayout):
    """Title + helper line on the left, switch on the right."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        active: bool = False,
        on_change: Optional[Callable[[bool], None]] = None,
        accent=theme.ACCENT,
        **kwargs,
    ):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(54) if subtitle else dp(42),
            spacing=dp(10),
            **kwargs,
        )
        self._on_change = on_change
        self._accent = accent

        text_col = BoxLayout(orientation="vertical", spacing=dp(1))
        head = Label(
            text=title,
            color=theme.TEXT,
            font_size=sp(14),
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(20),
        )
        head.bind(size=lambda w, *_: setattr(w, "text_size", (w.width, None)))
        text_col.add_widget(head)
        if subtitle:
            sub = Label(
                text=subtitle,
                color=theme.TEXT_FAINT,
                font_size=sp(10.5),
                halign="left",
                valign="top",
                size_hint_y=None,
                height=dp(26),
            )
            sub.bind(size=lambda w, *_: setattr(w, "text_size", (w.width, None)))
            text_col.add_widget(sub)
        self.add_widget(text_col)

        # AnchorLayout keeps the switch vertically centred in the row
        holder = AnchorLayout(size_hint_x=None, width=dp(52),
                              anchor_x="center", anchor_y="center")
        self.switch = AuroraSwitch(active=active)
        holder.add_widget(self.switch)
        self.add_widget(holder)
        self.switch.bind(active=self._changed)

    def _changed(self, _instance, value):
        if self._on_change:
            self._on_change(bool(value))

    def set_active(self, value: bool, notify: bool = False) -> None:
        """Sync the visual state from the store without echoing back."""
        self.switch.active = value
        if notify and self._on_change:
            self._on_change(bool(value))


class AuroraButton(ButtonBehavior, Label):
    """Rounded button with hover / press feedback."""

    def __init__(self, text="", accent=theme.ACCENT, on_press_action=None, **kwargs):
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", dp(44))
        super().__init__(
            text=text,
            color=theme.TEXT,
            font_size=sp(13),
            bold=True,
            **kwargs,
        )
        self.accent = accent
        self._action = on_press_action
        with self.canvas.before:
            self._c = Color(*theme.CARD_HI)
            self._bg = RoundedRectangle(radius=[dp(12)])
            self._edge = Color(*theme.fade(accent, 0.55))
            self._outline = Line(rounded_rectangle=(0, 0, 0, 0, dp(12)), width=1.2)
        self.bind(pos=self._sync, size=self._sync, state=self._sync)

    def _sync(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._outline.rounded_rectangle = (
            self.x,
            self.y,
            self.width,
            self.height,
            dp(12),
        )
        hovered = self.state == "down"
        self._c.rgba = theme.mix(theme.CARD_HI, self.accent, 0.22) if hovered else (
            theme.CARD_HI
        )
        self._edge.rgba = theme.fade(self.accent, 1.0 if hovered else 0.45)

    def on_release(self):
        if self._action:
            self._action()


class AuroraSlider(Widget):
    """Flat slider with a glowing knob; value range defaults to 0-100."""

    value = NumericProperty(0.0)
    min_value = NumericProperty(0.0)
    max_value = NumericProperty(100.0)

    def __init__(self, value=0.0, on_change=None, accent=theme.ACCENT, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(30))
        super().__init__(**kwargs)
        self._on_change = on_change
        self._accent = accent
        self._dragging = False
        with self.canvas:
            self._track_color = Color(*theme.TRACK)
            self._track = RoundedRectangle(radius=[dp(3)])
            self._fill_color = Color(*accent)
            self._fill = RoundedRectangle(radius=[dp(3)])
            self._knob_color = Color(*theme.TEXT)
            self._knob = Ellipse()
        self.bind(pos=self._sync, size=self._sync, value=self._sync)
        self.value = float(value)
        self._sync()

    def _knob_radius(self) -> float:
        return dp(8)

    def _sync(self, *_):
        r = self._knob_radius()
        span = max(1e-6, self.max_value - self.min_value)
        t = (self.value - self.min_value) / span
        t = max(0.0, min(1.0, t))
        track_h = dp(5)
        left = self.x + r
        right = self.x + self.width - r
        self._track.pos = (left, self.center_y - track_h / 2)
        self._track.size = (max(1.0, right - left), track_h)
        self._fill.pos = self._track.pos
        self._fill.size = (max(1.0, (right - left) * t), track_h)
        self._knob.pos = (left + (right - left) * t - r, self.center_y - r)
        self._knob.size = (r * 2, r * 2)
        self._fill_color.rgba = self._accent

    def _value_from_x(self, x: float) -> float:
        r = self._knob_radius()
        span = max(1e-6, self.width - r * 2)
        t = max(0.0, min(1.0, (x - self.x - r) / span))
        return self.min_value + t * (self.max_value - self.min_value)

    def _commit(self) -> None:
        if self._on_change:
            self._on_change(float(self.value))

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        self._dragging = True
        self.value = self._value_from_x(touch.x)
        self._commit()
        return True

    def on_touch_move(self, touch):
        if self._dragging:
            self.value = self._value_from_x(touch.x)
            self._commit()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self._dragging:
            self._dragging = False
            self._commit()
            return True
        return super().on_touch_up(touch)


class ValueRow(BoxLayout):
    """Caption + live value + slider."""

    def __init__(
        self,
        title: str,
        value: float,
        suffix: str = "%",
        on_change: Optional[Callable[[float], None]] = None,
        **kwargs,
    ):
        super().__init__(
            orientation="vertical", size_hint_y=None, height=dp(62), spacing=dp(2),
            **kwargs,
        )
        self._suffix = suffix
        head = BoxLayout(size_hint_y=None, height=dp(22))
        caption = Label(
            text=title, color=theme.TEXT, font_size=sp(13.5), halign="left",
            valign="middle",
        )
        caption.bind(size=lambda w, *_: setattr(w, "text_size", (w.width, None)))
        head.add_widget(caption)
        self.readout = Label(
            text=f"{value:.0f}{suffix}", color=theme.ACCENT, font_size=sp(13),
            bold=True, halign="right", valign="middle", size_hint_x=None, width=dp(64),
        )
        head.add_widget(self.readout)
        self.add_widget(head)

        def _changed(v):
            self.readout.text = f"{v:.0f}{suffix}"
            self.readout.color = theme.ACCENT
            if on_change:
                on_change(v)

        self.slider = AuroraSlider(value=value, on_change=_changed)
        self.add_widget(self.slider)


def styled_input(text: str = "", **kwargs) -> TextInput:
    """Dark, borderless input that matches the cards."""
    kwargs.setdefault("multiline", False)
    kwargs.setdefault("size_hint_y", None)
    kwargs.setdefault("height", dp(40))
    kwargs.setdefault("font_size", sp(13))
    return TextInput(
        text=text,
        background_normal="",
        background_active="",
        background_color=theme.BG_DEEP,
        foreground_color=theme.TEXT,
        cursor_color=theme.ACCENT,
        hint_text_color=theme.TEXT_FAINT,
        padding=[dp(10), dp(10)],
        **kwargs,
    )


class TinyLabel(Label):
    def __init__(self, text="", color=theme.TEXT_DIM, size=sp(10.5), **kwargs):
        super().__init__(text=text, color=color, font_size=size, **kwargs)
