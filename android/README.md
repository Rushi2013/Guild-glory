# Aurora Float — Android floating overlay panel

A complete, installable Android app: a draggable logo bubble floats above other
apps, tapping it opens a rounded dark panel with a **close (X) button**, live
toggles, sliders and preset pills. Built with **platform APIs only** — no
AndroidX, no third-party libraries, no assets beyond two vector drawables.

```
android/
├── app/src/main/AndroidManifest.xml     permissions + activity + overlay service
├── app/src/main/java/com/aurora/floatdeck/
│   ├── MainActivity.java     permission flow, start/stop, preferences UI
│   ├── OverlayService.java   foreground service, owns both overlay windows
│   ├── OverlayPanel.java     the panel card: header drag, X button, rows
│   ├── FloatingBubble.java   the logo bubble (gradient rounded square)
│   ├── Rows.java             section / toggle / slider row builders
│   ├── ToggleView.java       hand-drawn animated switch
│   ├── SliderView.java       hand-drawn draggable slider
│   ├── RoundButton.java      rounded button with press states
│   ├── CardView.java         rounded outlined card
│   ├── LogoView.java         the mark
│   ├── Prefs.java            SharedPreferences wrapper
│   └── Theme.java            palette + paint helpers
└── app/src/main/res/         adaptive icon, notification icon, dark theme
```

---

## ⚠️ Scope, stated plainly

This is an **overlay UI framework**, not a game mod. It draws its own window on
top of whatever is on screen and cannot read, control or modify another app's
process — so it contains no aimbot, ESP or teleport, and it never asks for
accessibility or usage-access permissions (the two things a real in-game cheat
overlay would need). The controls that *do* exist are wired to real behaviour:
opacity, snap-to-edge, haptics, auto-hide and the status ticker.

---

## Install the APK

**Option A — GitHub Actions artifact (already built):**

1. Open the **Actions** tab → *Android APK* → newest green run.
2. Download **aurora-float-apk** from the *Artifacts* section.
3. Unzip, copy `aurora-float-1.0.apk` to the phone, tap it.
4. Allow *Install unknown apps* for your file manager when asked.

**Option B — GitHub Release:** push a tag (`git tag v1.0 && git push origin v1.0`);
the workflow attaches the APK to a release automatically.

**After installing:**

1. Open **Aurora Float**.
2. Tap **Grant** on *Display over other apps* → enable it → back.
3. (Android 13+) Tap **Allow** on *Notifications*.
4. Tap **Show floating panel**. The bubble appears.
5. Tap the bubble → the panel opens. Drag the header to move it, press **✕** to
   close the panel, or use **Hide panel**. Stop everything from the app or the
   notification's **Stop** action.

---

## Build it yourself

**GitHub Actions (no local setup):** push to `main` or any `arena/**` branch that
touches `android/**`, or run the workflow manually from the Actions tab. It uses
JDK 17, provisions Gradle 8.7, runs `gradle assembleDebug` and uploads the APK.

**Android Studio:** *File → Open* → select the `android/` folder → let it sync →
*Run*.

**Command line** (needs JDK 17 + Android SDK with platform 34):

```bash
cd android
gradle wrapper --gradle-version 8.7   # once, creates ./gradlew
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

---

## Permissions — and why each one is there

| Permission | Why |
| --- | --- |
| `SYSTEM_ALERT_WINDOW` | "Display over other apps" — required to add a window above other apps |
| `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_SPECIAL_USE` | keeps the overlay alive while you are in other apps (Android 14 requires the special-use type and the manifest `<property>`) |
| `POST_NOTIFICATIONS` | the ongoing notification is mandatory for a foreground service and lets you stop the overlay |
| `VIBRATE` | optional haptic feedback on taps |

No internet, no accessibility, no usage stats, no storage.

---

## How it works

### 1. Two overlay windows

`OverlayService` asks the `WindowManager` for two `TYPE_APPLICATION_OVERLAY`
windows:

```java
new WindowManager.LayoutParams(
        bubbleSize, bubbleSize,
        WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
        PixelFormat.TRANSLUCENT);
```

`FLAG_NOT_FOCUSABLE` keeps the keyboard focus in the app underneath —
exactly what you want for a control panel, so tapping a toggle never steals input
from the app you are using. `FLAG_NOT_TOUCH_MODAL` lets touches outside the
bubble/panel pass through to the app below.

### 2. The bubble

`FloatingBubble` is a custom `View`: a gradient rounded square, an "A", and a cyan
dot that gains a brighter ring while the panel is open. It is *not* clickable —
the service attaches an `OnTouchListener` because moving the bubble means
rewriting `LayoutParams.x/y` and calling `windowManager.updateViewLayout()`.

The listener separates a **tap** from a **drag** with the system touch slop:

```java
if (!moved && (Math.abs(dx) > touchSlop || Math.abs(dy) > touchSlop)) moved = true;
...
if (!moved) { haptic(); togglePanel(); }        // tap  -> open / close panel
else { if (prefs.snapToEdge()) snapBubble(); }  // drag -> snap + remember
```

Snapping animates `LayoutParams.x` toward the nearest edge with a `ValueAnimator`,
and the final position is stored in `SharedPreferences` so the bubble reappears
where you left it.

### 3. The panel with the cross button

`OverlayPanel` is a rounded `CardView` (a `LinearLayout` that paints its own
background in `onDraw`) containing:

* **header** — logo, title, live status line, and the **✕ close button**
  (`RoundButton`, `\u2715` glyph). The header doubles as the drag handle: its
  `OnTouchListener` reports deltas, the service clamps them to the screen and
  updates the window. The ✕ is a real child button, so it consumes its own taps
  and never starts a drag.
* **body** — a `ScrollView` of shared row shapes from `Rows` (toggles, sliders,
  preset pills), so the panel and the app's settings screen render identically.
* **footer** — *Reset* and *Hide panel*.

Closing the panel removes only the panel window; the bubble stays until the
service stops. `onCloseRequested()` → `hidePanel()` → `windowManager.removeView(panel)`.

The panel is built fresh each time it opens, which is how it always reflects the
newest preferences without any observer plumbing.

### 4. Hand-drawn controls

* `ToggleView` — knob position is a float in `[0, 1]`; a 160 ms `ValueAnimator`
  interpolates it and every frame repaints, with the track colour blending from
  grey to the accent (`Theme.blend`) so the colour change happens mid-travel.
* `SliderView` — value ↔ pixel mapping plus snapping:
  `value = min + round((x - pad) / usable * (max - min))`, snapped to `step` and
  clamped; drawn as a rounded track, an accent fill and a white knob with a ring.
* `RoundButton` — a `TextView` with a `GradientDrawable` background; press state
  swaps the drawable for a darker fill in `onTouchEvent`.

### 5. Foreground service and the status line

A `NotificationChannel` + `startForeground()` keeps the process alive. On Android
14 the service declares `foregroundServiceType="specialUse"` (with the required
`<property>`) and calls:

```java
startForeground(id, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
```

While the panel is open, a `Handler` loop updates the status line at exactly the
rate set by the *UI refresh rate* slider (`1000 / hz` ms) — so that control does
something observable. The loop is stopped when the panel closes, and every touch
resets the optional 20-second auto-hide timer.

---

## Extending it

Add a control in three steps:

1. add a key + default to `Prefs` (getter/setter pair);
2. drop a row into `OverlayPanel.buildBody()`:
   `body.addView(Rows.toggleRow(context, "My switch", "What it does", prefs.myFlag(), callback, !prefs.reduceMotion()));`
3. react to it in `OverlayService.applySettings()`.

Re-skin everything from `Theme.COLORS` equivalents at the top of `Theme.java`.

## Release builds / signing

The CI artifact is a **debug** APK, which installs fine but:

* each CI run generates a fresh debug key, so installing a *new* build over an
  old one requires uninstalling first;
* the store/Play path needs a real key.

To ship properly signed builds, create a keystore once:

```bash
keytool -genkeypair -v -keystore aurora.jks -alias aurora \
  -keyalg RSA -keysize 2048 -validity 10000 -storepass <password>
```

add a `signingConfigs.release` block in `app/build.gradle`, and pass the password
through a CI secret. Never commit the keystore.

## Troubleshooting

* **Bubble disappears after a while** — some OEM skins (MIUI, ColorOS, One UI)
  kill background services. Allow *Autostart* / disable battery optimisation for
  Aurora Float.
* **"Display over other apps" greyed out** — on work profiles and some Android 14
  builds the toggle lives under *Settings → Apps → Special app access → Display
  over other apps*.
* **Panel opens but nothing responds** — the service was started without the
  overlay grant; stop it from the notification and re-grant.
