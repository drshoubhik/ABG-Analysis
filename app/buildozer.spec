[app]
title = ABG Analyser
package.name = abganalyser
package.domain = org.drshoubhik
version = 2.0

source.dir = .
source.include_exts = py,png,jpg,kv,ttf

# Pure Python + Kivy; no other dependencies
requirements = python3,kivy==2.3.1

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 24
# 64-bit ARM covers practically every phone from the last ~8 years
android.archs = arm64-v8a
android.accept_sdk_license = True
android.permissions =

# icon.filename = %(source.dir)s/icon.png

[buildozer]
log_level = 2
warn_on_root = 0
