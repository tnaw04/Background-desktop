# Animated wallpaper on GNOME Wayland

Render the existing square avatar and automatic eye routine into a silent 1920 × 1200 looping video. Extend the canvas with subdued ASCII digits in the same palette, 360 pixels on either side of the centered 1200-pixel avatar.

GNOME Shell draws its own backgrounds for the desktop, Activities Overview and workspace gestures. A user extension will feed the same decoded video frame into those backgrounds, preserving window previews and gesture handling. The existing X11 desktop window is suitable for the original interactive scene. The video path is sufficient for the approved automatic movement and integrates with GNOME's background layers.
