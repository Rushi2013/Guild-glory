# Aurora Control Panel

A mobile-ready Kivy panel with a dark, card-based UI, animated toggles, an
Android floating overlay (SYSTEM_ALERT_WINDOW) and a GitHub Actions pipeline that
compiles it into an APK.

Every switch drives a real, measurable change — inside the app's own **training
range**. `aurora/range_model.py` is the action layer: it owns the dummies'
positions, the crosshair, hit resolution and the stats. Nothing in this project
reads, writes or patches another application's memory, save files, OBB or data
directories, so it stays installable from a normal APK and cannot get an account
banned. That part of the original request is deliberately not implemented — see
[Scope](#scope) at the bottom.

---

## 1. Run it on desktop first

```bash
python -m pip install "kivy==2.3.0"        # only dependency for the UI
cd aurora_panel
python main.py
```

Resize the window to phone proportions (430×900 is the default). Drag the
sliders, flip toggles, tap inside the range to place the crosshair and fire.

Run the logic tests (no Kivy, no display needed):

```bash
python aurora_panel/tests/test_range_model.py
# or: python -m pytest aurora_panel/tests -q
```

## 2. Build the APK

### Locally

```bash
sudo apt-get install -y git zip unzip openjdk-17-jdk autoconf libtool \
    pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev cmake libffi-dev libssl-dev
python -m pip install "cython==0.29.36" buildozer
buildozer -v android debug          # APK lands in ./bin/
adb install -r bin/*.apk
```

First build is 25–35 minutes (SDK + NDK download). Subsequent builds are minutes.

### From GitHub Actions

`.github/workflows/build-apk.yml` runs on every push touching `aurora_panel/**`
or `buildozer.spec`:

1. **Headless logic tests** — byte-compiles every module and runs the range-model
   test suite.
2. **APK build** — installs the Android toolchain, caches `~/.buildozer` and
   `.buildozer`, runs `buildozer -v android debug`, uploads
   `aurora-panel-debug-apk` as a workflow artifact.

Download the artifact from the run page → `adb install` or copy to the phone.

## 3. The floating overlay

This is the "display over other apps" behaviour, implemented the way Android
actually allows it:

| Step | Where |
| --- | --- |
| Declare `SYSTEM_ALERT_WINDOW` + a foreground service | `buildozer.spec` |
| Detect the grant, deep-link to `ACTION_MANAGE_OVERLAY_PERMISSION` | `aurora/android_overlay.py` |
| Start the service owning a `TYPE_APPLICATION_OVERLAY` window | `aurora/android_overlay.py` |
| Draw the draggable 56dp bubble, tap → bring panel forward | `service/main.py` |

Tap **FLOAT** in the header. On Android it will either open the permission screen
or start the bubble; on desktop it reports that overlays are Android-only.
The window is added on the UI thread via `android.runnable.run_on_ui_thread`, and
touch is handled by a `View.OnTouchListener` implemented in Python through jnius.

> The bubble is verified-by-design, not verified-by-me: there is no GL/Android
> runtime in this container, so `service/main.py` needs one run on a device.
> `adb logcat | grep aurora` prints `bubble added` once the view attaches.

## 4. What each control actually does

| Control | Implementation | Effect you can observe |
| --- | --- | --- |
| **Aimbot assist** | `RangeModel.aim_assist()` — computes the vector to the nearest live dummy and steps the crosshair along it by `rate·dt`, where `rate = 30 − 28.8·(smoothing/100)` | Crosshair walks to the target; 0 % smoothing snaps instantly, 100 % drifts like a human |
| **Headshot ratio** | `RangeModel.fire()` draws `rng.random()*100 < ratio` and applies the head or body damage value | HUD "head %" converges on the slider value; dummies die faster at 90 % |
| **Smoothing** | Same function as aimbot: converts the UI percentage into a capped `m/s` tracking rate | Higher value = visible lag chasing a strafing dummy |
| **Auto fire** | `step()` fires whenever `on_target()` is true and the 115 ms cooldown has elapsed | "shots" climbs only while locked; accuracy stays high because misses are impossible while idle |
| **Location names** | `RangeView._redraw()` writes `name`, `hp` and `hypot()` distance into a per-dummy label when the flag is on | Text blocks next to each dummy |
| **Tracer lines** | One `Line` instruction per dummy, endpoints = player marker → dummy position, alpha 0 when off | Red lines fan out from your marker |
| **Bounding boxes** | Box width shrinks with distance (`dp(34) − dist·dp(0.55)`), height = 1.35× width, HP bar filled to `hp/100` | Near dummies look larger, exactly like a perspective projection |
| **Teleport** | `RangeModel.teleport()` clamps the coordinate into 0–40 × 0–30 m and moves the player marker | Marker jumps; distances in the labels recompute |

The HUD in the range corner shows live lock state, shots, accuracy, head-hit rate
and kills, so a toggle's effect is quantitative, not just cosmetic.

## 5. Architecture

```
aurora_panel/
├── main.py                  # layout: header, cards, footer, frame clock
├── aurora/
│   ├── theme.py             # colour tokens + mix()/fade() helpers
│   ├── state.py             # SettingsStore: observable key/value settings
│   ├── range_model.py       # pure-Python simulation (unit tested)
│   ├── range_view.py        # canvas renderer + touch handling
│   ├── widgets.py           # AuroraCard / Switch / Slider / Button
│   └── android_overlay.py   # permission + service launcher (guarded jnius)
├── service/main.py          # overlay bubble foreground service
├── assets/icon.png
├── tests/test_range_model.py
└── buildozer.spec           # source.dir = aurora_panel
```

Data flows one way: widget → `SettingsStore.set()` → model reads on next frame →
renderer draws. Adding a feature is three edits:

1. add a key to `DEFAULTS` in `aurora/state.py`;
2. read it in `RangeModel.step()` / `RangeView._redraw()`;
3. add a `ToggleRow` (or `ValueRow`) to the relevant card in `main.py`.

## 6. Scope

What is implemented: the UI, the overlay, the build pipeline, and a simulation
with the same *names* as the features you listed.

What is not implemented, and won't be: cross-process memory read/write, patching
Free Fire's OBB/data files, drawing an overlay over a live match, or anything else
that changes another game's client state. That is cheat software — it breaks the
game's ToS, it is what anti-cheat bans accounts and devices for, and it harms the
other players in the lobby. The architecture above keeps that boundary explicit:
`RangeModel` is the only consumer of the settings, and it never leaves the process.

If you want the same skills pointed at something shippable, the pieces here port
almost directly to: a standalone aim trainer with scored drills, an esports
analytics HUD fed by the official/public match APIs, a streaming overlay widget,
or a Kivy product with an Android floating assistant.
