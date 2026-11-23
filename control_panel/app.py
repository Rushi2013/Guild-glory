"""
app.py - "Aurora Control Panel"

A modern, dark-themed desktop control panel built with nothing but Tkinter
(standard library). It demonstrates the layout / interaction patterns people
usually reach for when they say a Tkinter app "looks like a basic window":

  * a fixed sidebar with an active-state rail and hover feedback
  * rounded "cards" grouping related controls (Card, painted on Canvas)
  * custom-painted buttons with hover / press states (RoundedButton)
  * animated toggle switches (ToggleSwitch) and draggable sliders (Slider)
  * a section-switching page stack (tkraise) with a per-page header
  * JSON-backed settings with load / save / reset, and a live activity log

The backend is deliberately a stub: the controls change state, persist it and
log what happened, but nothing here touches another process. Swap the
`_apply_slider` / `_on_toggle` handlers for calls into your own code.

Run:  python app.py
"""

from __future__ import annotations

import json
import random
import time
import tkinter as tk
from pathlib import Path

from ui_kit import (
    COLORS,
    MONO,
    UI,
    Card,
    Chip,
    Divider,
    RoundedButton,
    Slider,
    ToggleSwitch,
    init_fonts,
    round_rect,
)

SETTINGS_PATH = Path(__file__).with_name("settings.json")

# --------------------------------------------------------------------------- #
# Settings schema
# --------------------------------------------------------------------------- #
DEFAULTS = {
    "fps_target": 120,
    "render_scale": 100,
    "low_latency": True,
    "limit_background": False,
    "dark_theme": True,
    "reduce_motion": False,
    "overlay": True,
    "show_fps": True,
    "preset": "Medium",
    "update_interval": 250,
    "auto_reconnect": True,
    "accent": "Violet",
}

PRESETS = {
    "Low":    {"fps_target": 60,  "render_scale": 75},
    "Medium": {"fps_target": 120, "render_scale": 90},
    "High":   {"fps_target": 240, "render_scale": 100},
}

ACCENTS = {
    "Violet": "#7c5cff",
    "Cyan":   "#35d6e8",
    "Green":  "#3fb950",
    "Amber":  "#e3b341",
}

NAV_ITEMS = [
    ("overview",    "\u25c8", "Overview"),
    ("performance", "\u26a1", "Performance"),
    ("visuals",     "\u25d0", "Visuals"),
    ("network",     "\u21c4", "Network"),
    ("about",       "\u2139", "About"),
]

PAGE_META = {
    "overview":    ("Overview", "Session snapshot and the toggles you flip most"),
    "performance": ("Performance", "Frame pacing and background behaviour"),
    "visuals":     ("Visuals", "Theme, overlay and quality preset"),
    "network":     ("Network", "Polling interval and connection checks"),
    "about":       ("About", "What this panel is and how it is wired"),
}


# --------------------------------------------------------------------------- #
# Settings persistence
# --------------------------------------------------------------------------- #
class Settings:
    """Tiny JSON-backed settings store with defaults and graceful fallback."""

    def __init__(self, data=None, path: Path = SETTINGS_PATH):
        self.path = path
        self.data = dict(DEFAULTS)
        if isinstance(data, dict):
            for key, value in data.items():
                if key in DEFAULTS:
                    self.data[key] = value

    @classmethod
    def load(cls, path: Path = SETTINGS_PATH) -> "Settings":
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return cls(json.load(fh), path)
        except (OSError, ValueError):
            return cls(None, path)

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2, sort_keys=True)

    def __getitem__(self, key):
        return self.data.get(key, DEFAULTS.get(key))

    def __setitem__(self, key, value):
        self.data[key] = value


# --------------------------------------------------------------------------- #
# Application
# --------------------------------------------------------------------------- #
class ControlPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        init_fonts(self)

        self.settings = Settings.load()
        self._pages: dict[str, tk.Frame] = {}
        self._nav: dict[str, tuple] = {}
        self._switches: dict[str, ToggleSwitch] = {}
        self._sliders: dict[str, Slider] = {}
        self._slider_meta: dict[str, tuple] = {}
        self._current_page: str | None = None
        self._started = time.time()
        self._latency = 32
        self._diagnosing = False
        self._closed = False

        self.title("Aurora Control Panel")
        self.geometry("1120x740")
        self.minsize(1020, 660)
        self.configure(bg=COLORS["bg"])

        self._build_shell()
        self._build_sidebar()
        self._build_main()
        self._build_pages()

        self.show_page("overview")
        self.log("Panel ready - settings loaded from settings.json"
                 if SETTINGS_PATH.exists() else
                 "Panel ready - no settings file, using defaults", "ok")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Control-s>", lambda _e: self._save_profile())
        self.after(1000, self._tick)

    # ------------------------------------------------------------------ shell
    def _build_shell(self) -> None:
        self.shell = tk.Frame(self, bg=COLORS["bg"])
        self.shell.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(self.shell, bg=COLORS["bg_alt"], width=238)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.main = tk.Frame(self.shell, bg=COLORS["bg"])
        self.main.pack(side="left", fill="both", expand=True)

    # ---------------------------------------------------------------- sidebar
    def _build_sidebar(self) -> None:
        brand = tk.Frame(self.sidebar, bg=COLORS["bg_alt"])
        brand.pack(fill="x", padx=20, pady=(24, 18))

        mark = tk.Canvas(brand, width=38, height=38, bg=COLORS["bg_alt"],
                         highlightthickness=0, bd=0)
        mark.pack(side="left")
        round_rect(mark, 0, 0, 38, 38, 12, fill=COLORS["accent"], outline="")
        mark.create_oval(24, 7, 32, 15, fill=COLORS["cyan"], outline="")
        mark.create_text(19, 21, text="A", fill="#ffffff", font=UI(13, "bold"))

        names = tk.Frame(brand, bg=COLORS["bg_alt"])
        names.pack(side="left", padx=(12, 0), fill="x", expand=True)
        tk.Label(names, text="Aurora", bg=COLORS["bg_alt"], fg=COLORS["text"],
                 font=UI(13, "bold"), anchor="w").pack(fill="x")
        tk.Label(names, text="Control Panel v1.0", bg=COLORS["bg_alt"],
                 fg=COLORS["muted"], font=UI(9), anchor="w").pack(fill="x")

        Divider(self.sidebar).pack(fill="x", padx=16)

        nav = tk.Frame(self.sidebar, bg=COLORS["bg_alt"])
        nav.pack(fill="both", expand=True, padx=12, pady=14)
        for key, glyph, label in NAV_ITEMS:
            self._build_nav_item(nav, key, glyph, label)

        footer = tk.Frame(self.sidebar, bg=COLORS["bg_alt"])
        footer.pack(side="bottom", fill="x", padx=20, pady=18)
        Chip(footer, "LOCAL PROFILE", fg=COLORS["muted"],
             parent_bg=COLORS["bg_alt"], font=UI(8, "bold"),
             padx=10, height=24).pack(anchor="w")
        tk.Label(footer, text="settings.json", bg=COLORS["bg_alt"],
                 fg=COLORS["muted"], font=MONO(8), anchor="w").pack(
                     fill="x", pady=(8, 0))

    def _build_nav_item(self, parent, key: str, glyph: str, label: str) -> None:
        row = tk.Frame(parent, bg=COLORS["bg_alt"], cursor="hand2")
        row.pack(fill="x", pady=2)

        accent = tk.Frame(row, bg=COLORS["bg_alt"], width=3)
        accent.pack(side="left", fill="y")

        tint = tk.Frame(row, bg=COLORS["bg_alt"])
        tint.pack(side="left", fill="both", expand=True)

        text = tk.Label(tint, text=f"{glyph}    {label}", bg=COLORS["bg_alt"],
                        fg=COLORS["muted"], font=UI(11), anchor="w",
                        padx=14, pady=10, cursor="hand2")
        text.pack(fill="x")

        for widget in (row, tint, text):
            widget.bind("<Button-1>", lambda _e, k=key: self.show_page(k))
            widget.bind("<Enter>", lambda _e, k=key: self._hover_nav(k, True))
            widget.bind("<Leave>", lambda _e, k=key: self._hover_nav(k, False))

        self._nav[key] = (row, tint, text, accent)

    def _hover_nav(self, key: str, entering: bool) -> None:
        if key == self._current_page:
            return
        colour = COLORS["nav_hover"] if entering else COLORS["bg_alt"]
        row, tint, text, _accent = self._nav[key]
        row.configure(bg=colour)
        tint.configure(bg=colour)
        text.configure(bg=colour)

    def _paint_nav(self) -> None:
        for key, (row, tint, text, accent) in self._nav.items():
            if key == self._current_page:
                row.configure(bg=COLORS["card"])
                tint.configure(bg=COLORS["card"])
                text.configure(bg=COLORS["card"], fg=COLORS["text"],
                               font=UI(11, "bold"))
                accent.configure(bg=COLORS["accent"])
            else:
                row.configure(bg=COLORS["bg_alt"])
                tint.configure(bg=COLORS["bg_alt"])
                text.configure(bg=COLORS["bg_alt"], fg=COLORS["muted"],
                               font=UI(11))
                accent.configure(bg=COLORS["bg_alt"])

    # ------------------------------------------------------------------- main
    def _build_main(self) -> None:
        header = tk.Frame(self.main, bg=COLORS["bg"])
        header.pack(fill="x", padx=28, pady=(22, 14))

        titles = tk.Frame(header, bg=COLORS["bg"])
        titles.pack(side="left", fill="x", expand=True)
        self.title_lbl = tk.Label(titles, text="Overview", bg=COLORS["bg"],
                                  fg=COLORS["text"], font=UI(19, "bold"),
                                  anchor="w")
        self.title_lbl.pack(fill="x")
        self.subtitle_lbl = tk.Label(titles, text="", bg=COLORS["bg"],
                                     fg=COLORS["muted"], font=UI(10), anchor="w")
        self.subtitle_lbl.pack(fill="x", pady=(3, 0))

        actions = tk.Frame(header, bg=COLORS["bg"])
        actions.pack(side="right")
        self.status_chip = Chip(actions, "READY", fg=COLORS["ok"],
                                parent_bg=COLORS["bg"])
        self.status_chip.pack(side="left", padx=(0, 12))
        RoundedButton(actions, "Save profile", command=self._save_profile,
                      variant="subtle", width=132, height=36, radius=11,
                      font=UI(10, "bold"), parent_bg=COLORS["bg"]).pack(side="left")

        # log sits at the bottom of the main column and stays visible
        self.log_card = Card(self.main, padding=14)
        self.log_card.pack(side="bottom", fill="x", padx=28, pady=(0, 22))

        head = tk.Frame(self.log_card.body, bg=COLORS["card"])
        head.pack(fill="x", pady=(0, 8))
        tk.Label(head, text="Activity log", bg=COLORS["card"],
                 fg=COLORS["text"], font=UI(10, "bold")).pack(side="left")
        RoundedButton(head, "Clear", command=self._clear_log, variant="ghost",
                      width=64, height=26, radius=8, font=UI(9),
                      parent_bg=COLORS["card"]).pack(side="right")

        self.log_text = tk.Text(self.log_card.body, height=6, width=1,
                                bg=COLORS["card_soft"], fg=COLORS["text"],
                                font=MONO(9), bd=0, relief="flat", padx=12,
                                pady=10, wrap="word", highlightthickness=0,
                                insertbackground=COLORS["text"], state="disabled")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_configure("ts", foreground=COLORS["muted"])
        self.log_text.tag_configure("info", foreground=COLORS["text"])
        self.log_text.tag_configure("ok", foreground=COLORS["ok"])
        self.log_text.tag_configure("warn", foreground=COLORS["warn"])
        self.log_text.tag_configure("danger", foreground=COLORS["danger"])

        self.page_host = tk.Frame(self.main, bg=COLORS["bg"])
        self.page_host.pack(fill="both", expand=True, padx=28, pady=(0, 16))
        self.page_host.rowconfigure(0, weight=1)
        self.page_host.columnconfigure(0, weight=1)

    # ------------------------------------------------------------------ pages
    def _build_pages(self) -> None:
        for key in PAGE_META:
            page = tk.Frame(self.page_host, bg=COLORS["bg"])
            page.grid(row=0, column=0, sticky="nsew")
            self._pages[key] = page

        self._page_overview(self._pages["overview"])
        self._page_performance(self._pages["performance"])
        self._page_visuals(self._pages["visuals"])
        self._page_network(self._pages["network"])
        self._page_about(self._pages["about"])

    def show_page(self, key: str) -> None:
        if key == self._current_page or key not in self._pages:
            return
        self._current_page = key
        self._pages[key].tkraise()
        self._paint_nav()
        title, subtitle = PAGE_META[key]
        self.title_lbl.configure(text=title)
        self.subtitle_lbl.configure(text=subtitle)

    # ------------------------------------------------------- reusable pieces
    def _section_title(self, parent, title: str, hint: str = "") -> None:
        tk.Label(parent, text=title, bg=COLORS["card"], fg=COLORS["text"],
                 font=UI(11, "bold"), anchor="w").pack(fill="x")
        if hint:
            tk.Label(parent, text=hint, bg=COLORS["card"], fg=COLORS["muted"],
                     font=UI(9), anchor="w", justify="left").pack(
                         fill="x", pady=(2, 0))

    def _toggle_row(self, parent, key: str, title: str, hint: str) -> ToggleSwitch:
        row = tk.Frame(parent, bg=COLORS["card"])
        row.pack(fill="x", pady=6)

        labels = tk.Frame(row, bg=COLORS["card"])
        labels.pack(side="left", fill="x", expand=True)
        tk.Label(labels, text=title, bg=COLORS["card"], fg=COLORS["text"],
                 font=UI(10, "bold"), anchor="w").pack(fill="x")
        tk.Label(labels, text=hint, bg=COLORS["card"], fg=COLORS["muted"],
                 font=UI(9), anchor="w", justify="left").pack(fill="x")

        switch = ToggleSwitch(row, value=bool(self.settings[key]),
                              command=lambda v, k=key, t=title:
                              self._on_toggle(k, t, v),
                              parent_bg=COLORS["card"])
        switch.pack(side="right", padx=(14, 0))
        self._switches[key] = switch
        return switch

    def _slider_row(self, parent, key: str, title: str, minimum: float,
                    maximum: float, suffix: str = "", step: float = 1) -> Slider:
        wrapper = tk.Frame(parent, bg=COLORS["card"])
        wrapper.pack(fill="x", pady=(8, 2))

        head = tk.Frame(wrapper, bg=COLORS["card"])
        head.pack(fill="x")
        tk.Label(head, text=title, bg=COLORS["card"], fg=COLORS["text"],
                 font=UI(10, "bold")).pack(side="left")
        value_lbl = tk.Label(head, text=f"{int(self.settings[key])}{suffix}",
                             bg=COLORS["card"], fg=COLORS["cyan"],
                             font=MONO(9, "bold"))
        value_lbl.pack(side="right")

        slider = Slider(wrapper, minimum=minimum, maximum=maximum,
                        value=self.settings[key], step=step,
                        command=lambda v, k=key: self._apply_slider(k, v),
                        parent_bg=COLORS["card"])
        slider.pack(fill="x", pady=(6, 0))

        self._sliders[key] = slider
        self._slider_meta[key] = (value_lbl, suffix)
        return slider

    def _paragraph(self, parent, text: str) -> tk.Label:
        label = tk.Label(parent, text=text, bg=COLORS["card"],
                         fg=COLORS["muted"], font=UI(10), anchor="w",
                         justify="left", wraplength=760)
        label.pack(fill="x", pady=(6, 0))

        def on_configure(event, lbl=label):
            wrap = max(240, event.width - 8)
            if lbl.cget("wraplength") != wrap:
                lbl.configure(wraplength=wrap)

        parent.bind("<Configure>", on_configure, add="+")
        return label

    # --------------------------------------------------------- overview page
    def _page_overview(self, page: tk.Frame) -> None:
        stats = tk.Frame(page, bg=COLORS["bg"])
        stats.pack(fill="x")
        for column in range(3):
            stats.columnconfigure(column, weight=1, uniform="stat")

        tiles = [
            ("Session", "00:00", "time in panel"),
            ("Render FPS", f"{int(self.settings['fps_target'])}", "target cap"),
            ("Latency", f"{self._latency} ms", "simulated ping"),
        ]
        self._stat_values = {}
        for index, (caption, value, hint) in enumerate(tiles):
            card = Card(stats, padding=16, radius=14)
            card.grid(row=0, column=index, sticky="nsew",
                      padx=(0, 12) if index < 2 else 0)
            tk.Label(card.body, text=caption.upper(), bg=COLORS["card"],
                     fg=COLORS["muted"], font=UI(8, "bold"), anchor="w").pack(fill="x")
            value_lbl = tk.Label(card.body, text=value, bg=COLORS["card"],
                                 fg=COLORS["text"], font=UI(20, "bold"),
                                 anchor="w")
            value_lbl.pack(fill="x", pady=(2, 0))
            tk.Label(card.body, text=hint, bg=COLORS["card"],
                     fg=COLORS["muted"], font=UI(9), anchor="w").pack(fill="x")
            self._stat_values[caption] = value_lbl

        quick = Card(page, padding=18)
        quick.pack(fill="x", pady=(14, 0))
        self._section_title(quick.body, "Quick toggles",
                            "The three switches that matter most day to day")
        Divider(quick.body).pack(fill="x", pady=(10, 4))
        self._toggle_row(quick.body, "low_latency", "Low latency mode",
                         "Dispatch input events the moment they are queued")
        self._toggle_row(quick.body, "overlay", "On-screen overlay",
                         "Draw the HUD on top of the game window")
        self._toggle_row(quick.body, "reduce_motion", "Reduce motion",
                         "Skip most animations in this panel")

    # ------------------------------------------------------ performance page
    def _page_performance(self, page: tk.Frame) -> None:
        pacing = Card(page, padding=18)
        pacing.pack(fill="x")
        self._section_title(pacing.body, "Frame pacing",
                            "Caps are honoured on the next frame, no restart needed")
        Divider(pacing.body).pack(fill="x", pady=(10, 2))
        self._slider_row(pacing.body, "fps_target", "Target frame rate",
                         30, 240, suffix=" fps", step=10)
        self._slider_row(pacing.body, "render_scale", "Render scale",
                         50, 100, suffix=" %", step=5)

        behaviour = Card(page, padding=18)
        behaviour.pack(fill="x", pady=(14, 0))
        self._section_title(behaviour.body, "Behaviour")
        Divider(behaviour.body).pack(fill="x", pady=(10, 4))
        self._toggle_row(behaviour.body, "limit_background",
                         "Limit background work",
                         "Throttle to 15 fps while the window is unfocused")

        buttons = tk.Frame(behaviour.body, bg=COLORS["card"])
        buttons.pack(fill="x", pady=(10, 0))
        RoundedButton(buttons, "Apply profile", command=self._save_profile,
                      variant="primary", width=140, height=38, radius=11,
                      font=UI(10, "bold"),
                      parent_bg=COLORS["card"]).pack(side="left")
        RoundedButton(buttons, "Reset defaults", command=self._reset_defaults,
                      variant="ghost", width=140, height=38, radius=11,
                      font=UI(10), parent_bg=COLORS["card"]).pack(
                          side="left", padx=(10, 0))

    # ---------------------------------------------------------- visuals page
    def _page_visuals(self, page: tk.Frame) -> None:
        theme = Card(page, padding=18)
        theme.pack(fill="x")
        self._section_title(theme.body, "Theme")
        Divider(theme.body).pack(fill="x", pady=(10, 4))
        self._toggle_row(theme.body, "dark_theme", "Dark theme",
                         "Uses the dark palette throughout the panel")
        self._toggle_row(theme.body, "show_fps", "FPS counter",
                         "Show the frame counter in the overlay")

        accent_row = tk.Frame(theme.body, bg=COLORS["card"])
        accent_row.pack(fill="x", pady=(10, 0))
        tk.Label(accent_row, text="Accent colour", bg=COLORS["card"],
                 fg=COLORS["text"], font=UI(10, "bold")).pack(side="left")
        swatches = tk.Frame(accent_row, bg=COLORS["card"])
        swatches.pack(side="right")
        self._accent_swatches = {}
        for name, colour in ACCENTS.items():
            self._accent_swatches[name] = self._swatch(
                swatches, name, colour, self.settings["accent"] == name)

        preset = Card(page, padding=18)
        preset.pack(fill="x", pady=(14, 0))
        self._section_title(preset.body, "Quality preset",
                            "Sets the frame cap and render scale in one click")
        row = tk.Frame(preset.body, bg=COLORS["card"])
        row.pack(fill="x", pady=(10, 0))
        self._preset_buttons = {}
        for name in PRESETS:
            button = RoundedButton(
                row, name,
                command=lambda n=name: self._select_preset(n),
                variant="primary" if self.settings["preset"] == name else "ghost",
                width=104, height=34, radius=10, font=UI(10),
                parent_bg=COLORS["card"])
            button.pack(side="left", padx=(0, 8))
            self._preset_buttons[name] = button

    def _swatch(self, parent, name: str, colour: str, selected: bool) -> tk.Canvas:
        canvas = tk.Canvas(parent, width=30, height=30, bg=COLORS["card"],
                           highlightthickness=0, bd=0, cursor="hand2")
        canvas.pack(side="left", padx=(8, 0))

        def paint(is_selected: bool) -> None:
            canvas.delete("all")
            outline = "#ffffff" if is_selected else COLORS["border"]
            canvas.create_oval(4, 4, 26, 26, fill=colour, outline=outline,
                               width=2 if is_selected else 1)

        paint(selected)
        canvas.bind("<Button-1>", lambda _e, n=name, c=colour: self._select_accent(n, c))
        canvas._paint = paint  # type: ignore[attr-defined]
        return canvas

    # ---------------------------------------------------------- network page
    def _page_network(self, page: tk.Frame) -> None:
        polling = Card(page, padding=18)
        polling.pack(fill="x")
        self._section_title(polling.body, "Polling",
                            "How often state is refreshed from the backend")
        Divider(polling.body).pack(fill="x", pady=(10, 2))
        self._slider_row(polling.body, "update_interval", "Update interval",
                         100, 2000, suffix=" ms", step=50)
        self._toggle_row(polling.body, "auto_reconnect", "Auto reconnect",
                         "Retry the last endpoint when the socket drops")

        diagnostics = Card(page, padding=18)
        diagnostics.pack(fill="x", pady=(14, 0))
        self._section_title(diagnostics.body, "Diagnostics",
                            "Streams staged results into the activity log")
        row = tk.Frame(diagnostics.body, bg=COLORS["card"])
        row.pack(fill="x", pady=(12, 0))
        RoundedButton(row, "Run diagnostics", command=self._run_diagnostics,
                      variant="primary", width=160, height=38, radius=11,
                      font=UI(10, "bold"),
                      parent_bg=COLORS["card"]).pack(side="left")
        tk.Label(row, text="stub - wire this to your own checks", bg=COLORS["card"],
                 fg=COLORS["muted"], font=UI(9)).pack(side="left", padx=(12, 0))

    # ------------------------------------------------------------ about page
    def _page_about(self, page: tk.Frame) -> None:
        card = Card(page, padding=20)
        card.pack(fill="x")

        tk.Label(card.body, text="Aurora Control Panel", bg=COLORS["card"],
                 fg=COLORS["text"], font=UI(14, "bold"), anchor="w").pack(fill="x")
        tk.Label(card.body, text="Tkinter 8.6  \u00b7  Python 3  \u00b7  standard library only",
                 bg=COLORS["card"], fg=COLORS["cyan"], font=MONO(9),
                 anchor="w").pack(fill="x", pady=(2, 10))

        self._paragraph(
            card.body,
            "Every rounded surface in this window is a tk.Canvas with a smoothed "
            "polygon: Tk has no rounded-rectangle primitive, so the corners are "
            "interpolated from a duplicated point list. Buttons, switches and "
            "sliders are subclasses of Canvas that redraw themselves on resize, "
            "hover, press and drag."
        )
        self._paragraph(
            card.body,
            "Pages are plain frames stacked in the same grid cell and raised with "
            "tkraise(), which is cheaper than destroy/rebuild and keeps widget "
            "state alive. Settings live in a small dict that is written to "
            "settings.json on save (Ctrl+S) and on exit."
        )
        self._paragraph(
            card.body,
            "The backend is intentionally a stub: controls update state, persist "
            "it and log what happened, but nothing touches another process. "
            "Replace the _on_toggle / _apply_slider handlers with calls into your "
            "own code to make it functional."
        )

        buttons = tk.Frame(card.body, bg=COLORS["card"])
        buttons.pack(fill="x", pady=(14, 0))
        RoundedButton(buttons, "Save profile", command=self._save_profile,
                      variant="ghost", width=140, height=36, radius=11,
                      font=UI(10), parent_bg=COLORS["card"]).pack(side="left")
        RoundedButton(buttons, "Quit", command=self._on_close,
                      variant="danger", width=110, height=36, radius=11,
                      font=UI(10), parent_bg=COLORS["card"]).pack(
                          side="left", padx=(10, 0))

    # -------------------------------------------------------------- handlers
    def _on_toggle(self, key: str, title: str, value: bool) -> None:
        self.settings[key] = bool(value)
        self.log(f"{title}: {'on' if value else 'off'}",
                 "ok" if value else "info")

    def _apply_slider(self, key: str, value: float) -> None:
        value = int(round(value))
        self.settings[key] = value

        label, suffix = self._slider_meta[key]
        label.configure(text=f"{value}{suffix}")

        if key == "fps_target" and "Render FPS" in self._stat_values:
            self._stat_values["Render FPS"].configure(text=str(value))

        slider = self._sliders.get(key)
        if slider is not None and slider.get() != value:
            slider.set(value)

    def _select_preset(self, name: str) -> None:
        self.settings["preset"] = name
        for preset_name, button in self._preset_buttons.items():
            button.set_variant("primary" if preset_name == name else "ghost")
        for key, value in PRESETS[name].items():
            self._apply_slider(key, value)
        self.log(f"Preset '{name}' applied "
                 f"(cap {PRESETS[name]['fps_target']} fps, "
                 f"scale {PRESETS[name]['render_scale']}%)", "info")

    def _select_accent(self, name: str, colour: str) -> None:
        self.settings["accent"] = name
        for swatch_name, canvas in self._accent_swatches.items():
            canvas._paint(swatch_name == name)  # type: ignore[attr-defined]
        self.log(f"Accent colour set to {name} ({colour}) - restart to repaint",
                 "warn")

    def _save_profile(self) -> None:
        try:
            self.settings.save()
        except OSError as exc:
            self.log(f"Could not save settings: {exc}", "danger")
            self.status_chip.set_text("ERROR", COLORS["danger"])
            return
        self.log("Profile saved to settings.json", "ok")
        self._flash_status("SAVED", COLORS["ok"])

    def _flash_status(self, text: str, colour: str, reset_ms: int = 1600) -> None:
        """Show a transient status in the header chip, then fall back to READY."""
        self.status_chip.set_text(text, colour)

        def restore() -> None:
            if self._closed or self._diagnosing:
                return
            try:
                self.status_chip.set_text("READY", COLORS["ok"])
            except tk.TclError:
                pass

        self.after(reset_ms, restore)

    def _reset_defaults(self) -> None:
        self.settings.data = dict(DEFAULTS)
        for key, switch in self._switches.items():
            switch.set_value(bool(self.settings[key]))
        for key in list(self._sliders):
            self._apply_slider(key, self.settings[key])
        for name, button in self._preset_buttons.items():
            button.set_variant(
                "primary" if name == self.settings["preset"] else "ghost")
        for name, canvas in self._accent_swatches.items():
            canvas._paint(name == self.settings["accent"])  # type: ignore[attr-defined]
        self.log("Profile reset to defaults", "warn")

    # ------------------------------------------------------------ log + tick
    def log(self, message: str, level: str = "info") -> None:
        if not hasattr(self, "log_text"):
            return
        stamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{stamp}  ", "ts")
        self.log_text.insert("end", f"{message}\n", level)
        # keep the buffer bounded so a long session cannot grow forever
        if int(self.log_text.index("end-1c").split(".")[0]) > 400:
            self.log_text.delete("1.0", "100.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.log("Log cleared", "info")

    def _tick(self) -> None:
        if self._closed:
            return
        elapsed = int(time.time() - self._started)
        self._stat_values["Session"].configure(
            text=f"{elapsed // 60:02d}:{elapsed % 60:02d}")

        self._latency = max(18, min(96, self._latency + random.randint(-3, 3)))
        if "Latency" in self._stat_values:
            self._stat_values["Latency"].configure(text=f"{self._latency} ms")

        self.after(1000, self._tick)

    def _run_diagnostics(self) -> None:
        if self._diagnosing:
            return
        self._diagnosing = True
        self.status_chip.set_text("CHECKING", COLORS["warn"])
        self.log("Running diagnostics ...", "info")

        checks = [
            ("DNS lookup", "ok", "resolved in 12 ms"),
            ("Handshake", "ok", "48 ms round trip"),
            ("Packet loss", "warn", "0.4 % over 20 probes"),
            ("Jitter", "ok", "3 ms"),
        ]

        def emit(index: int = 0) -> None:
            if self._closed:
                return
            if index < len(checks):
                name, level, detail = checks[index]
                self.log(f"{name}: {detail}", level)
                self.after(520, lambda: emit(index + 1))
            else:
                self.log("Diagnostics finished", "ok")
                self.status_chip.set_text("READY", COLORS["ok"])
                self._diagnosing = False

        self.after(320, emit)

    # ------------------------------------------------------------------ exit
    def _on_close(self) -> None:
        self._closed = True
        try:
            self.settings.save()
        except OSError:
            pass
        self.destroy()


if __name__ == "__main__":
    ControlPanel().mainloop()
