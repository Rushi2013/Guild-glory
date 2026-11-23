"""Aurora Control Panel - entry point.

Run on desktop:      python main.py
Build an APK:        buildozer -v android debug   (see buildozer.spec)
CI:                  .github/workflows/build-apk.yml

The panel is a real UI: dark theme, rounded cards, animated toggles and sliders,
driving an in-app training-range simulation. It is intentionally self-contained -
the toggles only ever touch ``aurora.range_model.RangeModel``.
"""

from __future__ import annotations

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from aurora import android_overlay, theme
from aurora.range_model import RANGE_H, RANGE_W, RangeModel
from aurora.range_view import RangeView
from aurora.state import default_store
from aurora.widgets import (
    AuroraButton,
    AuroraCard,
    TinyLabel,
    ToggleRow,
    ValueRow,
    styled_input,
)


def _label(text, color=theme.TEXT, size=14, bold=False, height=None, halign="left"):
    widget = Label(
        text=text, color=color, font_size=sp(size), bold=bold, halign=halign,
        valign="middle", size_hint_y=None,
    )
    widget.height = height or dp(20)
    widget.bind(size=lambda w, *_: setattr(w, "text_size", (w.width, None)))
    return widget


class Backdrop(FloatLayout):
    """Solid base + two soft accent glows, drawn once, no images shipped."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(*theme.BG)
            self._base = Rectangle()
            Color(*theme.fade(theme.ACCENT, 0.10))
            self._glow_a = Ellipse()
            Color(*theme.fade(theme.VIOLET, 0.09))
            self._glow_b = Ellipse()
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._base.pos = self.pos
        self._base.size = self.size
        w, h = self.size
        self._glow_a.pos = (self.x - w * 0.35, self.top - h * 0.30)
        self._glow_a.size = (w * 0.95, w * 0.95)
        self._glow_b.pos = (self.right - w * 0.45, self.top - h * 0.24)
        self._glow_b.size = (w * 0.8, w * 0.8)


class AuroraPanel(App):
    title = "Aurora Control Panel"

    # -- build --------------------------------------------------------------
    def build(self):
        Window.clearcolor = theme.BG
        if not android_overlay.IS_ANDROID:
            Window.size = (430, 900)
            Window.minimum_width, Window.minimum_height = 360, 620

        self.store = default_store()
        self.model = RangeModel(self.store)
        self._status_text = ""

        root = FloatLayout()
        root.add_widget(Backdrop())

        shell = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            padding=[dp(12), dp(10), dp(12), dp(8)],
        )
        shell.add_widget(self._build_header())

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3),
                            bar_color=theme.fade(theme.ACCENT, 0.5),
                            bar_inactive_color=theme.fade(theme.BORDER, 0.6))
        content = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=dp(12),
            padding=[dp(2), dp(8), dp(2), dp(16)],
        )
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(self._build_range_card())
        content.add_widget(self._build_combat_card())
        content.add_widget(self._build_visuals_card())
        content.add_widget(self._build_movement_card())
        content.add_widget(self._build_notes_card())
        scroll.add_widget(content)
        shell.add_widget(scroll)
        shell.add_widget(self._build_footer())
        root.add_widget(shell)

        Clock.schedule_interval(self._tick, 1 / 45.0)
        self.store.bind("*", self._on_any_change)
        return root

    # -- header / footer ----------------------------------------------------
    def _build_header(self):
        header = BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(10),
                           padding=[dp(4), 0, dp(4), 0])
        titles = BoxLayout(orientation="vertical", spacing=0)
        titles.add_widget(_label("AURORA", theme.TEXT, 24, True, dp(28)))
        titles.add_widget(
            _label("CONTROL PANEL  ·  TRAINING BUILD", theme.TEXT_FAINT, 9.5,
                   False, dp(16))
        )
        header.add_widget(titles)

        self.float_btn = AuroraButton(
            text="FLOAT", accent=theme.VIOLET, size_hint=(None, None),
            size=(dp(78), dp(38)), on_press_action=self._toggle_float_overlay,
        )
        header.add_widget(self.float_btn)
        return header

    def _build_footer(self):
        bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8),
                        padding=[dp(6), dp(4), dp(6), dp(4)])
        left = BoxLayout(orientation="vertical", spacing=0)
        left.add_widget(_label("SIMULATION BUILD", theme.LIME, 9.5, True, dp(14)))
        self.status = _label(
            "In-app range only · no external process is read or modified",
            theme.TEXT_FAINT, 8.5, False, dp(14),
        )
        left.add_widget(self.status)
        bar.add_widget(left)
        self.active_count = _label("0 ON", theme.ACCENT, 11, True, dp(16), "right")
        self.active_count.size_hint_x = None
        self.active_count.width = dp(52)
        bar.add_widget(self.active_count)
        return bar

    # -- cards --------------------------------------------------------------
    def _build_range_card(self):
        card = AuroraCard(title="Target range", accent=theme.LIME,
                          fixed_height=dp(268))

        self.range_view = RangeView(self.model, size_hint=(1, 1))
        card.add_widget(self.range_view)

        controls = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        controls.add_widget(
            AuroraButton(
                text="RESET STATS", size_hint=(1, None), height=dp(34),
                on_press_action=self._reset_stats,
            )
        )
        controls.add_widget(
            AuroraButton(
                text="RESPAWN DUMMIES", accent=theme.LIME, size_hint=(1, None),
                height=dp(34), on_press_action=self._respawn,
            )
        )
        card.add_widget(controls)
        return card

    def _build_combat_card(self):
        card = AuroraCard(title="Combat", accent=theme.ACCENT)
        card.add_widget(
            ToggleRow(
                "Aimbot assist",
                "Pulls the crosshair to the nearest dummy at the set smoothing rate",
                active=bool(self.store.get("aimbot")),
                on_change=lambda v: self.store.set("aimbot", v),
            )
        )
        card.add_widget(
            ValueRow(
                "Headshot ratio", float(self.store.get("headshot_ratio")),
                suffix="%", on_change=lambda v: self.store.set("headshot_ratio", v),
            )
        )
        card.add_widget(
            ValueRow(
                "Smoothing", float(self.store.get("aim_smoothing")), suffix="%",
                on_change=lambda v: self.store.set("aim_smoothing", v),
            )
        )
        card.add_widget(
            ToggleRow(
                "Auto fire", "Fires while the crosshair is inside a dummy's hitbox",
                active=bool(self.store.get("auto_fire")),
                on_change=lambda v: self.store.set("auto_fire", v),
            )
        )
        return card

    def _build_visuals_card(self):
        card = AuroraCard(title="Visuals", accent=theme.VIOLET)
        for key, title, subtitle in (
            ("location_esp", "Location names",
             "Name, HP and distance printed beside each dummy"),
            ("line_esp", "Tracer lines", "Line from your position to each dummy"),
            ("box_esp", "Bounding boxes",
             "Perspective box scaled by distance, with an HP bar"),
        ):
            card.add_widget(
                ToggleRow(
                    title, subtitle, active=bool(self.store.get(key)),
                    on_change=lambda v, k=key: self.store.set(k, v),
                )
            )
        return card

    def _build_movement_card(self):
        card = AuroraCard(title="Movement", accent=theme.AMBER)

        coords = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        coords.add_widget(TinyLabel("X", theme.TEXT_FAINT, 11, size_hint_x=None,
                                    width=dp(14)))
        self.input_x = styled_input(f"{float(self.store.get('teleport_x')):.0f}")
        coords.add_widget(self.input_x)
        coords.add_widget(TinyLabel("Y", theme.TEXT_FAINT, 11, size_hint_x=None,
                                    width=dp(14)))
        self.input_y = styled_input(f"{float(self.store.get('teleport_y')):.0f}")
        coords.add_widget(self.input_y)
        card.add_widget(coords)

        card.add_widget(
            AuroraButton(
                "TELEPORT TO COORDINATE", accent=theme.AMBER,
                on_press_action=self._teleport,
            )
        )
        card.add_widget(
            TinyLabel(
                f"Range bounds: 0-{RANGE_W:.0f} m × 0-{RANGE_H:.0f} m. "
                "Out-of-range values are clamped.",
                theme.TEXT_FAINT, 9,
            )
        )
        return card

    def _build_notes_card(self):
        card = AuroraCard(title="How this build works", accent=theme.TEXT_DIM)
        for line in (
            "· UI layer: Kivy widgets drawn with canvas vectors - no image assets.",
            "· Action layer: every toggle writes to SettingsStore, RangeModel reads it.",
            "· RangeModel is pure Python and unit-tested in tests/test_range_model.py.",
            "· FLOAT asks Android for SYSTEM_ALERT_WINDOW, then starts a foreground "
            "service that owns the bubble window.",
        ):
            lab = _label(line, theme.TEXT_DIM, 9.5, False, dp(30))
            lab.text_size = (dp(320), None)
            card.add_widget(lab)
        return card

    # -- actions ------------------------------------------------------------
    def _tick(self, dt):
        self.range_view.tick(dt)

    def _reset_stats(self):
        from aurora.range_model import Stats

        self.model.stats = Stats()
        self._set_status("Stats reset")

    def _respawn(self):
        for enemy in self.model.enemies:
            enemy.alive, enemy.hp = True, 100.0
        self._set_status("Dummies respawned")

    def _teleport(self):
        try:
            x = float(self.input_x.text)
            y = float(self.input_y.text)
        except ValueError:
            self._set_status("Enter numeric X / Y coordinates")
            return
        pos = self.model.teleport(x, y)
        self.store.set("teleport_x", pos[0])
        self.store.set("teleport_y", pos[1])
        self._set_status(f"Teleported to {pos[0]:.0f}, {pos[1]:.0f} m")

    def _toggle_float_overlay(self):
        status = android_overlay.ensure_overlay()
        if status is None:
            self._set_status("Floating bubble service started")
        else:
            self._set_status(status)

    def _set_status(self, text: str, color=theme.TEXT_FAINT):
        self.status.text = text
        self.status.color = color

    def _on_any_change(self, _key, _value):
        on = sum(
            1 for k in ("aimbot", "auto_fire", "location_esp", "line_esp", "box_esp")
            if self.store.get(k)
        )
        self.active_count.text = f"{on} ON"
        self.active_count.color = theme.ACCENT if on else theme.TEXT_FAINT


if __name__ == "__main__":
    AuroraPanel().run()
