"""Headless tests for the simulation + settings store (no Kivy needed).

    python -m pytest aurora_panel/tests -q
    # or, without pytest:
    python aurora_panel/tests/test_range_model.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora.range_model import HIT_RADIUS, RangeModel  # noqa: E402
from aurora.state import SettingsStore, default_store  # noqa: E402


def _stepped(model, seconds=3.0, dt=1 / 60.0):
    for _ in range(int(seconds / dt)):
        model.step(dt)
    return model


# -- store -------------------------------------------------------------------
def test_store_notifies_only_on_real_change():
    store = SettingsStore(box_esp=False)
    seen = []
    store.bind("box_esp", lambda k, v: seen.append(v))
    store.set("box_esp", False)
    store.set("box_esp", True)
    store.set("box_esp", True)
    assert seen == [True]


def test_store_wildcard_listener():
    store = default_store()
    seen = []
    store.bind("*", lambda k, v: seen.append(k))
    store.set("aimbot", True)
    store.set("line_esp", True)
    assert seen == ["aimbot", "line_esp"]


# -- range model -------------------------------------------------------------
def test_aimbot_acquires_and_holds_target():
    store = SettingsStore(aimbot=True, aim_smoothing=0.0, auto_fire=False)
    model = _stepped(RangeModel(store), seconds=6.0)
    target = model.on_target()
    assert target is not None, "crosshair should be locked after a few seconds"
    assert model.distance(model.crosshair, target.pos) <= HIT_RADIUS


def test_without_aimbot_crosshair_is_idle():
    store = SettingsStore(aimbot=False, auto_fire=False)
    model = RangeModel(store)
    start = model.crosshair
    _stepped(model, seconds=2.0)
    assert model.crosshair == start


def test_auto_fire_only_shoots_on_target():
    store = SettingsStore(aimbot=True, aim_smoothing=0.0, auto_fire=True)
    model = _stepped(RangeModel(store), seconds=6.0)
    assert model.stats.shots > 0
    assert model.stats.hits > 0
    # after a lock is acquired the accuracy should be high, not random spraying
    assert model.stats.accuracy > 50.0


def test_auto_fire_off_never_shoots():
    store = SettingsStore(aimbot=True, aim_smoothing=0.0, auto_fire=False)
    model = _stepped(RangeModel(store), seconds=4.0)
    assert model.stats.shots == 0


def test_headshot_ratio_is_respected():
    low = SettingsStore(aimbot=True, aim_smoothing=0.0, auto_fire=True,
                        headshot_ratio=0.0)
    high = SettingsStore(aimbot=True, aim_smoothing=0.0, auto_fire=True,
                         headshot_ratio=100.0)
    low_model = _stepped(RangeModel(low, seed=3), seconds=12.0)
    high_model = _stepped(RangeModel(high, seed=3), seconds=12.0)
    assert low_model.stats.head_hits == 0
    assert high_model.stats.head_hits == high_model.stats.hits > 0


def test_kill_and_respawn_cycle():
    store = SettingsStore(aimbot=True, aim_smoothing=0.0, auto_fire=True,
                          headshot_ratio=100.0)
    model = _stepped(RangeModel(store), seconds=15.0)
    assert model.stats.kills >= 1
    # dummies come back after RESPAWN_DELAY
    _stepped(model, seconds=6.0)
    assert len(model.living()) >= 1


def test_teleport_clamps_into_bounds():
    model = RangeModel(default_store())
    assert model.teleport(-40, 900) == (0.0, 30.0)
    assert model.teleport(12.5, 8.0) == (12.5, 8.0)


def test_manual_move_and_fire_hits():
    model = RangeModel(default_store())
    model.settings.set("auto_fire", False)
    enemy = model.living()[0]
    model.move_crosshair(*enemy.pos)
    hit = model.fire()
    assert hit is enemy
    assert enemy.hp < 100.0
    assert model.stats.hits == 1


def test_readout_is_json_friendly():
    model = _stepped(RangeModel(default_store()), seconds=1.0)
    snap = model.readout()
    assert isinstance(snap["crosshair"], tuple)
    assert isinstance(snap["alive"], int)
    assert snap["shots"] == 0


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    raise SystemExit(1 if failures else 0)
