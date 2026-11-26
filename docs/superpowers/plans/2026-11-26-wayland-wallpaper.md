# Wayland Wallpaper Implementation Plan

> For agentic workers: Execute the tasks in order and verify each before proceeding.

**Goal** — Run the animated avatar and both digit bands on Ubuntu GNOME Wayland.

**Architecture** — Render existing face glyphs into an in-memory RGB surface and encode a WebM loop. The GNOME Shell 46 extension replays lossless crops of those same frames on a shared still backdrop. This reduces texture updates to the eye region.

**Tech stack** — Python, NumPy, Pillow, GStreamer and GJS.

**Spec** — [Animated wallpaper on GNOME Wayland](../specs/2026-11-26-wayland-wallpaper-design.md)

## Constraints and verification

- [x] Check 1920 × 1200 in-memory rendering, both digit bands, the centered full-height avatar and changing eye pixels without pointer input.
- [x] Verify that the exporter writes a seekable 1920 × 1200 WebM loop and matching playback frames.
- [x] Capture the desktop, Overview and a partial workspace swipe in a GNOME Shell 46 Wayland test session. Confirm that playback wraps to the beginning.
- [x] Install the extension and verify that GNOME's enabled list includes it. The real desktop is still on Xorg and needs a Wayland login to load the extension.
