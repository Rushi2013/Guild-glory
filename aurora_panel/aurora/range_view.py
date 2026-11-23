"""The in-app training range viewport.

A 2D top-down sandbox drawn with canvas instructions. It is the thing the
toggles actually control, which makes the panel demonstrable end-to-end without
touching any other process on the device.
"""

from __future__ import annotations

from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from . import theme
from .range_model import RANGE_H, RANGE_W, RangeModel


class RangeView(Widget):
    def __init__(self, model: RangeModel, **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self._enemy_art = []        # per-dummy canvas instructions
        self._labels = []           # per-dummy text labels (local coords)
        self._label_timer = 0.0

        with self.canvas:
            # backdrop
            self._bg = Color(*theme.BG_DEEP)
            self._bg_rect = RoundedRectangle(radius=[dp(12)])
            # grid
            self._grid_color = Color(*theme.fade(theme.BORDER, 0.85))
            self._grid = Line(width=1.0)
            # ESP lines (one instruction per dummy, reused every frame)
            self._line_esp = []
            for _ in model.enemies:
                self._line_color = Color(*theme.fade(theme.DANGER, 0.0))
                self._line_esp.append(
                    (self._line_color, Line(points=[], width=dp(1.1)))
                )
            # player
            self._player_color = Color(*theme.LIME)
            self._player_dot = Ellipse()
            self._player_ring = Line(width=dp(1.4), ellipse=(0, 0, 0, 0))
            # dummies
            for _ in model.enemies:
                box_c = Color(*theme.fade(theme.VIOLET, 0.0))
                box = Line(width=dp(1.6))
                hp_bg_c = Color(*theme.fade(theme.BG, 0.0))
                hp_bg = RoundedRectangle(radius=[dp(2)])
                hp_c = Color(*theme.fade(theme.LIME, 0.0))
                hp_fill = RoundedRectangle(radius=[dp(2)])
                self._enemy_art.append(
                    dict(box_color=box_c, box=box, hp_bg_color=hp_bg_c, hp_bg=hp_bg,
                         hp_color=hp_c, hp=hp_fill)
                )
            # crosshair
            self._cross_color = Color(*theme.ACCENT)
            self._cross_ring = Line(width=dp(1.2), ellipse=(0, 0, 0, 0))
            self._cross_a = Line(width=dp(1.4))
            self._cross_b = Line(width=dp(1.4))
            self._flash_color = Color(*theme.fade(theme.AMBER, 0.0))
            self._flash = Ellipse()

        for enemy in model.enemies:
            label = Label(
                text="", markup=True, font_size=sp(9.5), color=theme.TEXT,
                size_hint=(None, None), halign="left", valign="middle",
            )
            label.bind(size=lambda w, *_: setattr(w, "text_size", (w.width, w.height)))
            label.opacity = 0.0
            self._labels.append(label)
            self.add_widget(label)

        self._hud = Label(
            text="[b]TRAINING RANGE[/b]  ·  in-app simulation",
            markup=True, font_size=sp(10), color=theme.TEXT_FAINT,
            size_hint=(None, None), halign="left", valign="middle",
        )
        self.add_widget(self._hud)
        self._stats = Label(
            text="", markup=True, font_size=sp(10), color=theme.TEXT_DIM,
            size_hint=(None, None), halign="right", valign="middle",
        )
        self.add_widget(self._stats)

        self.bind(pos=self._relayout, size=self._relayout)

    # -- coordinates --------------------------------------------------------
    def _scale(self):
        return self.width / RANGE_W, self.height / RANGE_H

    def _local(self, x, y):
        sx, sy = self._scale()
        return x * sx, y * sy

    def _abs(self, x, y):
        lx, ly = self._local(x, y)
        return self.x + lx, self.y + ly

    def world_from_touch(self, pos):
        sx, sy = self._scale()
        return ((pos[0] - self.x) / max(sx, 1e-6), (pos[1] - self.y) / max(sy, 1e-6))

    # -- layout -------------------------------------------------------------
    def _relayout(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

        step = 5.0
        pts = []
        x = 0.0
        while x <= RANGE_W:
            pts += list(self._abs(x, 0)) + list(self._abs(x, RANGE_H))
            x += step
        y = 0.0
        while y <= RANGE_H:
            pts += list(self._abs(0, y)) + list(self._abs(RANGE_W, y))
            y += step
        self._grid.points = pts

        self._hud.pos = (self.x + dp(10), self.top - dp(20))
        self._hud.text_size = (self.width - dp(20), dp(16))
        self._stats.pos = (self.x + dp(10), self.y + dp(6))
        self._stats.text_size = (self.width - dp(20), dp(14))

    # -- frame --------------------------------------------------------------
    def tick(self, dt: float) -> None:
        self.model.step(dt)
        self._redraw(dt)

    def _redraw(self, dt: float) -> None:
        model = self.model
        settings = model.settings
        show_box = bool(settings.get("box_esp"))
        show_line = bool(settings.get("line_esp"))
        show_loc = bool(settings.get("location_esp"))
        locked = model.on_target()

        # player
        px, py = self._abs(*model.player)
        r = dp(5)
        self._player_dot.pos = (px - r, py - r)
        self._player_dot.size = (r * 2, r * 2)
        self._player_ring.ellipse = (px - r * 2, py - r * 2, r * 4, r * 4)

        # dummies
        for i, enemy in enumerate(model.enemies):
            art = self._enemy_art[i]
            label = self._labels[i]
            if not enemy.alive:
                for key in ("box_color", "hp_bg_color", "hp_color"):
                    art[key].rgba = theme.fade(theme.BG, 0.0)
                for key in ("box", "hp_bg", "hp"):
                    if key == "box":
                        art[key].points = []
                    else:
                        art[key].size = (0, 0)
                label.opacity = 0.0
                self._line_esp[i][0].rgba = theme.fade(theme.DANGER, 0.0)
                continue

            ex, ey = self._abs(*enemy.pos)
            dist = RangeModel.distance(model.player, enemy.pos)
            box_w = max(dp(16), dp(34) - dist * dp(0.55))
            box_h = box_w * 1.35
            left = ex - box_w / 2
            bottom = ey - box_h / 2
            alpha = 0.95 if enemy is locked else 0.55

            art["box_color"].rgba = theme.fade(
                theme.DANGER if enemy is locked else theme.VIOLET, alpha if show_box else 0.0
            )
            art["box"].points = (
                [left, bottom, left + box_w, bottom,
                 left + box_w, bottom + box_h, left, bottom + box_h, left, bottom]
                if show_box else []
            )

            hp_frac = max(0.0, min(1.0, enemy.hp / 100.0))
            bar_w, bar_h = box_w, dp(3)
            art["hp_bg_color"].rgba = theme.fade(theme.BG, 0.9 if show_box else 0.0)
            art["hp_bg"].pos = (left, bottom - dp(6))
            art["hp_bg"].size = (bar_w, bar_h) if show_box else (0, 0)
            art["hp_color"].rgba = theme.fade(
                theme.LIME if hp_frac > 0.5 else (theme.AMBER if hp_frac > 0.2 else theme.DANGER),
                0.95 if show_box else 0.0,
            )
            art["hp"].pos = (left, bottom - dp(6))
            art["hp"].size = (bar_w * hp_frac, bar_h) if show_box else (0, 0)

            lc, line = self._line_esp[i]
            lc.rgba = theme.fade(theme.DANGER, 0.35 if show_line else 0.0)
            line.points = [px, py, ex, ey] if show_line else []

            if show_loc:
                label.text = (
                    f"[b]{enemy.name}[/b]\n"
                    f"[color=8a94ad]{dist:0.1f} m · hp {int(enemy.hp)}[/color]"
                )
                lx, ly = self._local(enemy.pos[0], enemy.pos[1])
                label.size = (dp(92), dp(26))
                label.pos = (lx + box_w / 2 + dp(6), ly - dp(13))
                label.opacity = 1.0
            else:
                label.opacity = 0.0

        # crosshair
        cx, cy = self._abs(*model.crosshair)
        rad = dp(9)
        self._cross_color.rgba = theme.DANGER if locked else theme.ACCENT
        self._cross_ring.ellipse = (cx - rad, cy - rad, rad * 2, rad * 2)
        arm = dp(6)
        gap = dp(3)
        self._cross_a.points = [cx - arm - gap, cy, cx - gap, cy,
                                cx + gap, cy, cx + arm + gap, cy]
        self._cross_b.points = [cx, cy - arm - gap, cx, cy - gap,
                                cx, cy + gap, cx, cy + arm + gap]

        if model.flash > 0:
            fr = dp(13)
            self._flash_color.rgba = theme.fade(theme.AMBER, 0.55)
            self._flash.pos = (cx - fr, cy - fr)
            self._flash.size = (fr * 2, fr * 2)
        else:
            self._flash_color.rgba = theme.fade(theme.AMBER, 0.0)
            self._flash.size = (0, 0)

        # HUD numbers at ~10 Hz so we are not re-laying out text every frame
        self._label_timer += dt
        if self._label_timer > 0.1:
            self._label_timer = 0.0
            s = model.stats
            lock_txt = f"[color=ff5c72]LOCK {locked.name}[/color]" if locked else "no lock"
            self._stats.text = (
                f"{lock_txt}   shots {s.shots}   acc {s.accuracy:0.0f}%   "
                f"head {s.head_rate:0.0f}%   kills {s.kills}"
            )

    # -- input --------------------------------------------------------------
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        world = self.world_from_touch(touch.pos)
        if self.model.settings.get("aimbot", False):
            # with assist on, a tap is just a shot: the assist owns the crosshair
            self.model.fire()
        else:
            self.model.move_crosshair(*world)
            self.model.fire()
        return True
