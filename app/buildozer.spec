[app]
title = ABG Analyser
package.name = abganalyser
package.domain = org.drshoubhik
version = 2.0

source.dir = .
source.include_exts = py,png,jpg,kv,ttf

# Pure Python + Kivy; no other dependencies
requirements = python3,kivy==2.3.0

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 24
# 64-bit ARM covers practically every phone from the last ~8 years
android.archs = arm64-v8a
android.accept_sdk_license = True
android.ndk = 25b

# Pin python-for-android to the release made for Buildozer 1.5.0
# (Python 3.11.5, Kivy 2.3.0, NDK 25b). Its newer releases build Python 3.14
# and expect NDK 28c, which Buildozer 1.5.0 does not set up.
p4a.branch = v2024.01.21
android.permissions =

# Release builds are signed with our own key (see the CI workflow); output an APK
# that installs directly, not the Play Store .aab bundle Buildozer defaults to.
android.release_artifact = apk

# icon.filename = %(source.dir)s/icon.png

[buildozer]
log_level = 2
warn_on_root = 0
