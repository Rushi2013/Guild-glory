# Aurora Control Panel — a modern Tkinter control panel

A dark-themed desktop control panel built with **nothing but the Python standard
library**. It is a reusable UI layer: rounded cards, custom-painted buttons,
animated toggle switches, draggable sliders, a sidebar page stack, JSON-backed
settings and a live activity log.

```
control_panel/
├── ui_kit.py     reusable widgets (Card, RoundedButton, ToggleSwitch, Slider, Chip)
├── app.py        the demo application built from those widgets
└── README.md     this file
```

---

## ⚠️ What this is *not*

This is **not** a game mod / cheat panel, and it contains no aimbot, ESP or
teleport code. I'm not going to write those:

* Aimbot, ESP and teleport work by reading and patching another process's memory
  (or hooking its renderer / network stream) inside a live multiplayer match.
  That gives you an advantage over real people who did not consent to it, and it
  breaks Riot-style/Free Fire-style terms of service and anti-cheat rules — the
  realistic outcome is a permanent ban on the account, and in some regions an
  actual legal problem under anti-circumvention and computer-misuse laws.
* "Python GUI code" cannot do it anyway. A Tkinter window is an ordinary OS
  window; it has no access to another game's memory, so the panel would only be
  a skin over a process-injection DLL. The GUI is the easy 10%; the part that
  actually matters is the part I won't help with.

What *is* here is the part people usually get stuck on — making Tkinter not look
like Tkinter — plus the architecture to hang real functionality on.

Legitimate ways to build the same skills:

* write your own game (pygame) and implement aim-assist / ESP-style HUD there —
  you control both sides, so nothing is unfair;
* mod **offline, single-player** games where the publisher ships modding tools;
* build an aim trainer, a HUD overlay for your own app, or a stats dashboard;
* study anti-cheat: run your own client/server lab and detect the cheats instead.

---

## Install

You need Python 3.9+ **with Tk** — no `pip install` is required.

| Platform | What to do |
| --- | --- |
| Windows / macOS (python.org installer) | Tk is included, nothing to install |
| Debian / Ubuntu / Kali | `sudo apt update && sudo apt install python3-tk` |
| Fedora | `sudo dnf install python3-tkinter` |
| Arch | `sudo pacman -S tk` |
| Termux (Android) | `pkg install python-tkinter x11-repo` then run under a VNC/X server |

Check it:

```bash
python -c "import tkinter; print('Tk', tkinter.TkVersion)"
```

Optional extras, only if you want to extend it:

```bash
pip install pillow      # PNG icons / image assets
pip install pyqt5       # a heavier, more native-looking toolkit
```

## Run

```bash
cd control_panel
python app.py
```

Shortcuts: **Ctrl+S** saves the profile. Closing the window also saves.
Settings land in `control_panel/settings.json` (deleted = back to defaults).

---

## How the UI logic works

### 1. Rounded corners — `round_rect()`

Tk has no rounded-rectangle primitive and no anti-aliased shapes. The standard
workaround is a **smoothed polygon**: give `create_polygon` a point list where each
corner point is repeated, then `smooth=True` interpolates a spline through it. The
duplicated points flatten the spline along the edges, so only the corners curve.

```python
points = [x1+r, y1,  x2-r, y1,  x2, y1,
          x2, y1+r, x2, y2-r,  x2, y2,
          x2-r, y2, x1+r, y2,  x1, y2,
          x1, y2-r, x1, y1+r,  x1, y1]
canvas.create_polygon(points, smooth=True, fill=..., outline=...)
```

### 2. Cards that size themselves — `Card`

A card is a `tk.Frame` holding two children:

* a `Canvas` filling the frame, painting the rounded surface **behind** everything;
* a `body` `Frame` where you put your widgets, inset by `padding` so its square
  corners never poke out of the rounded outline.

Two `<Configure>` bindings do the work: when the card is resized it repaints and
re-widths `body`; when `body` changes height (because you added a row) the card
sets its own height to `body height + 2 × padding`. Result: you never hard-code
pixel heights, and sections stay grouped visually.

### 3. Buttons — `RoundedButton`

A `tk.Canvas` subclass with a small state machine — `normal → hover → press` —
driven by `<Enter>`, `<Leave>`, `<ButtonPress-1>`, `<ButtonRelease-1>`. Every state
change repaints the polygon with a different fill, and the command only fires if
the mouse is still inside the widget on release (the same behaviour as a native
button). Variants are just palettes: `primary`, `ghost`, `subtle`, `danger`.

### 4. Toggle switches — `ToggleSwitch`

The knob position is a float `_t` in `[0, 1]`. Clicking flips a boolean and calls
`_animate()`, which nudges `_t` toward its target every 12 ms via `after()` and
redraws — that interpolation is what makes it feel physical instead of snapping.
The track colour switches on `_t > 0.5`, so the colour change happens mid-travel.

### 5. Sliders — `Slider`

Value ↔ pixel conversion is the whole widget:

```python
ratio = (value - minimum) / (maximum - minimum)
x     = padding + ratio * (width - 2 * padding)      # draw
ratio = (event.x - padding) / (width - 2 * padding)  # drag
value = minimum + clamp(ratio, 0, 1) * (maximum - minimum)
```

Then the value is snapped to `step` and clamped, the track is drawn as two
round-capped lines (grey full width, accent up to the knob), and a white circle
marks the knob. `<Button-1>` sets the value immediately, `<B1-Motion>` keeps
dragging while the button is held.

### 6. Pages — one grid cell, `tkraise()`

Every page is a plain `Frame` placed in the *same* grid cell of the page host
(`row=0, column=0, sticky="nsew"`), so they stack. Switching sections is one call
to `tkraise()` — no destroy/rebuild, so widget state and scroll positions survive,
and switching is instant. The sidebar highlights the active item by repainting a
3 px accent rail and swapping the label to bold.

### 7. Settings — `Settings`

A dict with defaults, filtered on load so a stale `settings.json` can't inject
unknown keys, written with `json.dump(..., indent=2)` on save/exit. Every control
writes straight into it; nothing else holds state, which is what makes "reset to
defaults" a five-line operation (set dict = defaults, then push values back into
the widgets with `notify=False` so no change events fire).

### 8. Activity log — `tk.Text`

A disabled `Text` widget used as an append-only console. `log()` re-enables it,
inserts a muted timestamp plus a level-tagged line (`ok` / `warn` / `danger` all
map to tag colours defined with `tag_configure`), scrolls to the end with
`see("end")` and disables it again. The buffer is trimmed past 400 lines so a long
session can't grow without bound.

### 9. Diagnostics — `after()` instead of threads

"Run diagnostics" streams four results into the log with a 520 ms gap. It does
that with a recursive `after()` callback, not a thread, because **Tkinter is not
thread-safe**: touching a widget from a worker thread causes random crashes. If
you wire in real work, do it in a thread and post results back to the UI with a
`queue.Queue` polled by `after(50, ...)`.

---

## Extending it

Add a control in three steps:

1. add the key + default to `DEFAULTS`;
2. drop `self._toggle_row(card.body, "my_key", "My control", "what it does")` or
   `self._slider_row(card.body, "my_key", "My slider", 0, 100, suffix=" %")`
   into any page;
3. handle it in `_on_toggle` / `_apply_slider` (currently: store + log).

Re-skin everything from the single `COLORS` dict in `ui_kit.py`; all widgets read
from it at paint time.
