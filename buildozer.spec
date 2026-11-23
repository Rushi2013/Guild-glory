[app]

# Build the panel only - source.dir points at aurora_panel/ so the APK does not
# drag in the rest of this repository.
title = Aurora Panel
package.name = aurorapanel
package.domain = ai.arena

source.dir = aurora_panel
source.include_exts = py,png,jpg,kv,atlas,ttf,json
source.exclude_dirs = tests,bin,__pycache__,build,dist
source.exclude_patterns = *.pyc,*.pyo,.DS_Store

version = 1.0.0

requirements = python3,kivy==2.3.0

orientation = portrait
fullscreen = 0
# status bar stays visible; adjust to 1 if you want a true kiosk look
android.api = 34
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a, armeabi-v7a
android.private_storage = True
android.accept_sdk_license = True

# The floating bubble needs the special "display over other apps" grant plus a
# foreground service to keep the overlay window alive while the panel is
# backgrounded.
android.permissions = SYSTEM_ALERT_WINDOW,FOREGROUND_SERVICE,FOREGROUND_SERVICE_SPECIAL_USE,POST_NOTIFICATIONS,WAKE_LOCK
services = AuroraFloat:service/main.py

icon.filename = %(source.dir)s/assets/icon.png

android.entrypoint = org.kivy.android.PythonActivity
android.apptheme = "@android:style/Theme.NoTitleBar"
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 1
