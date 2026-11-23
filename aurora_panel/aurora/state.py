"""Observable settings store.

Every toggle / slider writes through ``SettingsStore.set`` and every widget that
cares subscribes with ``bind``. That keeps the UI layer and the simulation layer
decoupled: the range model never imports Kivy, and the UI never reaches into the
model's internals.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

LISTENER = Callable[[str, Any], None]


class SettingsStore:
    """Tiny key/value store with change notifications.

    >>> s = SettingsStore()
    >>> seen = []
    >>> s.bind("box_esp", lambda k, v: seen.append((k, v)))
    >>> s.set("box_esp", True)
    >>> seen
    [('box_esp', True)]
    """

    def __init__(self, **defaults: Any) -> None:
        self._values: Dict[str, Any] = dict(defaults)
        self._listeners: Dict[str, List[LISTENER]] = {}

    # -- read ---------------------------------------------------------------
    def get(self, key: str, fallback: Any = None) -> Any:
        return self._values.get(key, fallback)

    def __getitem__(self, key: str) -> Any:
        return self._values[key]

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._values)

    # -- write --------------------------------------------------------------
    def set(self, key: str, value: Any) -> Any:
        if self._values.get(key) == value:
            return value
        self._values[key] = value
        for listener in list(self._listeners.get(key, ())):
            listener(key, value)
        for listener in list(self._listeners.get("*", ())):
            listener(key, value)
        return value

    def toggle(self, key: str) -> bool:
        return bool(self.set(key, not self.get(key, False)))

    # -- observe ------------------------------------------------------------
    def bind(self, key: str, listener: LISTENER) -> None:
        """Subscribe to one key, or to ``"*"`` for every change."""
        self._listeners.setdefault(key, []).append(listener)

    def unbind(self, key: str, listener: LISTENER) -> None:
        if listener in self._listeners.get(key, ()):
            self._listeners[key].remove(listener)


DEFAULTS = dict(
    # combat
    aimbot=False,
    aim_smoothing=35.0,       # 0 = snap, 100 = slow / human-ish
    headshot_ratio=60.0,      # share of shots resolved as head hits, %
    auto_fire=False,
    # visuals
    location_esp=False,
    line_esp=False,
    box_esp=False,
    # movement
    teleport_x=20.0,
    teleport_y=15.0,
)


def default_store() -> SettingsStore:
    return SettingsStore(**DEFAULTS)
