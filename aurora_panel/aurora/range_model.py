"""Target-range simulation.

This is the "action layer" of the demo: a self-contained 2D training range that
lives entirely inside the app. It is a plain Python module (no Kivy import) so it
can be unit-tested headlessly and so the rules of the sim are readable on their
own.

It does not read, patch or talk to any other application. The toggles in the
panel drive *this* model only, which is what makes it safe to ship and useful as
a playground for the UI work.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

Point = Tuple[float, float]

RANGE_W = 40.0          # metres
RANGE_H = 30.0

HEAD_DAMAGE = 58.0      # training-dummy damage table
BODY_DAMAGE = 24.0
HIT_RADIUS = 1.10       # metres: crosshair-to-centre distance that counts as a hit
FIRE_COOLDOWN = 0.115   # seconds between auto-fire rounds (~520 RPM)
RESPAWN_DELAY = 2.0


@dataclass
class Enemy:
    name: str
    centre: Point
    orbit: float = 4.0
    phase: float = 0.0
    speed: float = 0.55
    hp: float = 100.0
    alive: bool = True
    respawn_at: float = 0.0
    pos: Point = field(default=(0.0, 0.0))

    def step(self, t: float, dt: float) -> None:
        angle = self.phase + t * self.speed
        x = self.centre[0] + math.cos(angle) * self.orbit
        y = self.centre[1] + math.sin(angle * 0.8) * self.orbit * 0.7
        self.pos = (
            min(RANGE_W - 0.5, max(0.5, x)),
            min(RANGE_H - 0.5, max(0.5, y)),
        )


@dataclass
class Stats:
    shots: int = 0
    hits: int = 0
    head_hits: int = 0
    damage: float = 0.0
    kills: int = 0

    @property
    def accuracy(self) -> float:
        return (self.hits / self.shots * 100.0) if self.shots else 0.0

    @property
    def head_rate(self) -> float:
        return (self.head_hits / self.hits * 100.0) if self.hits else 0.0


class RangeModel:
    """Deterministic training range.

    Parameters
    ----------
    settings:
        Anything with a ``get(key, default)`` method - normally a
        :class:`aurora.state.SettingsStore`.
    seed:
        Keeps the dummy patrol and the head/body rolls reproducible in tests.
    """

    def __init__(self, settings, seed: int = 7) -> None:
        self.settings = settings
        self.rng = random.Random(seed)
        self.t = 0.0
        self.crosshair: Point = (RANGE_W / 2, RANGE_H / 2)
        self.player: Point = (RANGE_W / 2, 2.0)
        self.stats = Stats()
        self.cooldown = 0.0
        self.last_shot_was_head = False
        self.flash = 0.0          # seconds of muzzle flash left, for the view
        self.enemies: List[Enemy] = self._spawn_dummies()
        self._roll = random.Random(seed + 1)

    # -- setup --------------------------------------------------------------
    @staticmethod
    def _spawn_dummies() -> List[Enemy]:
        specs = [
            ("Dummy-01", (9.0, 21.0), 3.4, 0.0, 0.70),
            ("Dummy-02", (20.0, 24.0), 5.0, 1.9, 0.45),
            ("Dummy-03", (31.0, 20.0), 3.8, 3.4, 0.62),
            ("Dummy-04", (14.0, 10.0), 4.6, 5.1, 0.38),
            ("Dummy-05", (28.0, 9.0), 4.0, 2.2, 0.52),
        ]
        return [Enemy(n, c, o, p, s) for n, c, o, p, s in specs]

    # -- geometry -----------------------------------------------------------
    @staticmethod
    def distance(a: Point, b: Point) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def living(self) -> List[Enemy]:
        return [e for e in self.enemies if e.alive]

    def nearest(self) -> Optional[Enemy]:
        alive = self.living()
        if not alive:
            return None
        return min(alive, key=lambda e: self.distance(self.crosshair, e.pos))

    def on_target(self) -> Optional[Enemy]:
        target = self.nearest()
        if target and self.distance(self.crosshair, target.pos) <= HIT_RADIUS:
            return target
        return None

    # -- actions ------------------------------------------------------------
    def teleport(self, x: float, y: float) -> Point:
        """Clamp the requested coordinate into the range and move there."""
        self.player = (
            max(0.0, min(RANGE_W, float(x))),
            max(0.0, min(RANGE_H, float(y))),
        )
        return self.player

    def aim_assist(self, dt: float) -> None:
        """Pull the crosshair toward the nearest dummy's head point."""
        target = self.nearest()
        if target is None:
            return
        smoothing = float(self.settings.get("aim_smoothing", 35.0))
        # 0 -> instant snap (cap 30/s), 100 -> very gradual (1.2/s)
        rate = 30.0 - 28.8 * (smoothing / 100.0)
        step = rate * dt
        dx = target.pos[0] - self.crosshair[0]
        dy = target.pos[1] - self.crosshair[1]
        dist = math.hypot(dx, dy)
        if dist <= step or dist == 0.0:
            self.crosshair = target.pos
            return
        self.crosshair = (
            self.crosshair[0] + dx / dist * step,
            self.crosshair[1] + dy / dist * step,
        )

    def fire(self) -> Optional[Enemy]:
        """Resolve one shot at the current crosshair position."""
        if self.cooldown > 0:
            return None
        target = self.on_target()
        self.cooldown = FIRE_COOLDOWN
        self.flash = 0.06
        self.stats.shots += 1
        if target is None:
            return None

        ratio = float(self.settings.get("headshot_ratio", 60.0))
        head = self._roll.random() * 100.0 < ratio
        self.last_shot_was_head = head
        dmg = HEAD_DAMAGE if head else BODY_DAMAGE
        target.hp -= dmg
        self.stats.hits += 1
        self.stats.damage += dmg
        if head:
            self.stats.head_hits += 1
        if target.hp <= 0:
            target.hp = 0.0
            target.alive = False
            target.respawn_at = self.t + RESPAWN_DELAY
            self.stats.kills += 1
        return target

    def move_crosshair(self, x: float, y: float) -> None:
        self.crosshair = (
            max(0.0, min(RANGE_W, float(x))),
            max(0.0, min(RANGE_H, float(y))),
        )

    # -- frame --------------------------------------------------------------
    def step(self, dt: float) -> None:
        dt = max(0.0, min(0.1, dt))
        self.t += dt
        self.cooldown = max(0.0, self.cooldown - dt)
        self.flash = max(0.0, self.flash - dt)

        for enemy in self.enemies:
            if enemy.alive:
                enemy.step(self.t, dt)
            elif self.t >= enemy.respawn_at:
                enemy.alive = True
                enemy.hp = 100.0
                enemy.step(self.t, dt)

        if self.settings.get("aimbot", False):
            self.aim_assist(dt)

        if self.settings.get("auto_fire", False) and self.on_target():
            self.fire()

    # -- reporting ----------------------------------------------------------
    def readout(self) -> Dict[str, object]:
        """Snapshot used by the HUD and by tests."""
        target = self.on_target()
        return {
            "time": round(self.t, 2),
            "crosshair": (round(self.crosshair[0], 2), round(self.crosshair[1], 2)),
            "player": (round(self.player[0], 2), round(self.player[1], 2)),
            "locked": target.name if target else None,
            "alive": len(self.living()),
            "shots": self.stats.shots,
            "hits": self.stats.hits,
            "head_rate": round(self.stats.head_rate, 1),
            "accuracy": round(self.stats.accuracy, 1),
            "kills": self.stats.kills,
        }
