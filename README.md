# eyes-desktop

**A live ASCII wallpaper for Linux whose eyes follow your mouse.**

A portrait is redrawn in thousands of characters across the whole screen. The eyes track the pointer, the pupils widen and narrow, the lids blink, the hair sways in the wind and parts when you brush the pointer through it, and clicking the water sends out ripples. It runs as a real wallpaper behind your windows, with no browser.

[Tiếng Việt](README.vi.md)

![The wallpaper following the pointer, rippling the water and swaying the hair](demo/face.gif)

One eye at full size, so the glyphs can be read (the iris fibres are `\ | / (` characters radiating from the pupil):

![Close-up of one eye following the pointer](demo/eye-closeup.gif)

| Dark theme | Light theme | `eye` scene |
|---|---|---|
| ![Dark theme](demo/face-dark.png) | ![Light theme](demo/face-light.png) | ![The single eye scene](demo/eye-scene.png) |

## Features

**`face` scene (default):**

- **Fills the screen.** Works on 16:9, 16:10, 21:9, any resolution and multiple monitors.
- **Eyes follow the mouse.** Each eyeball is painted afresh:
  - shaded white, with the upper lid's shadow;
  - an iris rebuilt from the picture's own iris, with radial fibres, a collarette ring, a dark rim and two catchlights.
  - The iris slides *behind* the real lid lines and squashes as it turns towards a corner, like a round eyeball. Both eyes aim separately.
- **Pupils** narrow when the pointer comes close and widen when it moves away.
- **Lids.** They blink at random (sometimes twice), blink on big glances, squint when the pointer sits right on an eye, and drop when the eyes look down. A closing lid is skin-toned and carries the lash line on its rim.
- **Hair.**
  - It sways along the direction the strands grow, tips more than roots, in gusts.
  - Move the pointer through it and it is brushed aside, then springs back.
- **Water.** It ripples gently. A click sends out a ring, and the pointer leaves a small wake as it glides over the water.
- **Sparkles and glow.** Specks in the hair twinkle, and a soft light follows the pointer.
- **When the mouse rests,** the eyes play a little routine of their own: glancing aside, reading, squinting, blinking.

**`eye` scene:** a single ASCII eye that follows the mouse, from the author's GitHub profile card.

**Light on resources.**
- Only what changed is redrawn, straight to the window with libX11.
- Pointer effects run only while the pointer is over the wallpaper itself.
- Everything pauses while a maximised or fullscreen window covers the screen.

## Requirements

- **X11** for pointer tracking. On Ubuntu, choose **"Ubuntu on Xorg"** using the gear icon on the login screen.
- **GNOME 46 on Wayland** for automatic animated wallpaper. Run `./install-wayland.sh` from the project folder. The exporter requires GStreamer with `gst-launch-1.0`, `rawvideoparse`, `vp8enc` and `webmmux`. Log out and back into Wayland if GNOME has yet to discover the extension.
- **Python 3.8+** with Tk, Pillow, NumPy and python-xlib.
- A monospace font. DejaVu Sans Mono is used if present, otherwise whatever `fc-match monospace` finds.

Install the packages once.

Debian / Ubuntu:

```bash
sudo apt install python3-tk python3-pil python3-pil.imagetk python3-xlib python3-numpy
```

Fedora:

```bash
sudo dnf install python3-tkinter python3-pillow-tk python3-xlib python3-numpy
```

Arch:

```bash
sudo pacman -S tk python-pillow python-xlib python-numpy
```

In a virtualenv instead, install your distribution's Tk package as above, then:

```bash
pip install -r requirements.txt
```

## Quick start

```bash
git clone https://github.com/hdnng/eyes-desktop.git
```

```bash
cd eyes-desktop
```

Try it in a normal 1280x720 window (Esc to quit):

```bash
python3 eyes.py --window
```

Make it your wallpaper, now and at every login:

```bash
./install.sh
```

`install.sh` writes `~/.config/autostart/eyes-desktop.desktop` (your user only, nothing system-wide) and starts the wallpaper. Keep the folder where it is afterwards: the autostart entry points to it.

Everyday commands:

| Command | What it does |
|---|---|
| `./start.sh` | (re)start the wallpaper, for example after editing `config.json` |
| `./stop.sh` | stop it |
| `./uninstall.sh` | stop it and remove it from autostart |

The log is in `~/.cache/eyes-desktop.log`.

## Configuration

Edit `config.json`, then run `./start.sh`. Any key can also be given once on the command line, for example `./start.sh --theme light --cell 4`.

| Key | Meaning | Default |
|---|---|---|
| `scene` | `"face"` or `"eye"` | `"face"` |
| `theme` | `"dark"` or `"light"` | `"dark"` |
| `fit` | face: `"cover"` fills the screen; `"contain"` shows the whole picture centred | `"cover"` |
| `focus` | face, cover: the point of the picture put at the screen centre, `[x, y]` from 0 to 1. Raise `y` for more nose and water, lower it for more hair | `[0.5, 0.5]` |
| `cell` | face: character width in px at 1080p. Smaller means more detail and more CPU. Scales with resolution | `5` |
| `hair_strength` | how far the hair sways | `3.5` |
| `face_size` | face, contain: picture size as a fraction of the screen height | `0.92` |
| `size` | eye scene: eye height as a fraction of the screen height | `0.6` |
| `position` | contain / eye scene: centre of the picture, `[x, y]` | `[0.5, 0.5]` |
| `monitor` | `"primary"` or a monitor index (`0`, `1`, …) | `"primary"` |
| `fps` | frames per second for the eyes and pointer effects | `24` |
| `ambient_fps` | frames per second for hair and water (at least 20 while ripples spread) | `12` |
| `idle_after` | seconds without mouse movement before the idle routine starts | `8.0` |
| `effects` | switch effects on or off: `water`, `ripples`, `hair`, `stars`, `glow` | all on |
| `background` | a background colour of your own, e.g. `"#000000"` | from the theme |
| `font` | path to another monospace font | DejaVu Sans Mono Bold |

## Use your own picture

The face scene is driven by two files:

| File | Contents |
|---|---|
| `assets/avatar.png` | a square picture, ideally a close-up where both eyes are clearly visible |
| `assets/face.json` | the picture's geometry, in its own pixels |

The geometry in `face.json`:

| Field | Meaning |
|---|---|
| `eyes[].upper` / `eyes[].lower` | points along the upper and lower edge of each eye opening, from the inner corner to the outer one, both starting and ending at the same corners |
| `eyes[].iris` | `[x, y, radius]` of the iris |
| `eyes[].lid` | thickness of the dark lash band just above the opening (`lash`), and how much skin above it the closing lid uses (`skin`) |
| `hair[]` | one or more hair regions: a `polygon`, the `root` the strands grow from, the `direction` towards their tips, and how long they are (`reach`) |
| `water.top` / `water.full` | where water (if any) starts, and where it is fully in motion. Set `top` below the picture's height to have none |
| `stars` | how far down to look for bright specks to twinkle |

To set it up:

1. Replace `assets/avatar.png` with your picture.
2. Edit the points in `assets/face.json` to match it.
3. Draw the geometry over the picture:

   ```bash
   python3 tools/check_geometry.py
   ```

4. Open `geometry-check.png`: lids are red and blue, irises green, hair yellow with an arrow for the strand direction, the water line cyan. Adjust the points and repeat until they sit on the picture.
5. Try the result with `python3 eyes.py --window`.

## Recording the demo

`tools/record_demo.py` recreates the images in `demo/` on a virtual screen. It needs `Xvfb` and `xdotool`:

```bash
python3 tools/record_demo.py
```

```bash
python3 tools/record_demo.py --still-only --theme light --prefix face-light
```

## Performance

Measured at 1080p on the test machine, as a share of one CPU core:

| State | CPU |
|---|---|
| Face scene, all effects, pointer resting | about 18% |
| Face scene, all effects, pointer brushing the hair | about 23% |
| Face scene, eyes only (`hair` and `water` off) | about 7% |
| A maximised or fullscreen window in front | about 0% (paused) |

The hair costs the most. For less CPU, lower `ambient_fps` (e.g. 8), raise `cell` (e.g. 6), or turn `hair` off.

## Troubleshooting

| Symptom | What to do |
|---|---|
| The eyes do not follow the mouse | Check `echo $XDG_SESSION_TYPE`. If it says `wayland`, log in with an X11 session (see Requirements). |
| Desktop icons disappear or cover the wallpaper | With a desktop-icons extension (e.g. GNOME's Desktop Icons NG), stacking depends on start order. Run `./start.sh` again after logging in. Clicks on the water may go to the icons layer instead. |
| `No monospace font found` | Install DejaVu Sans Mono (`fonts-dejavu-core` on Debian/Ubuntu), or set `"font"` in `config.json`. |
| `note: direct X drawing unavailable` in the log | The display is not 24-bit TrueColor, so Tk images are used instead. Everything works, just with more CPU. |
| Anything else | Look in `~/.cache/eyes-desktop.log`. |

## How it works

| File | Role |
|---|---|
| `eyes.py` | the wallpaper window (`_NET_WM_WINDOW_TYPE_DESKTOP`, below all apps); reads the pointer through Xlib, follows monitor changes, pauses when covered |
| `behaviour.py` | where the eyes look, pupil size, blinks, and the idle routine |
| `scene_face.py` | each frame, resamples the picture through a displacement field (hair, water, ripples), paints both eyeballs, and converts the result to characters |
| `ascii_render.py` | ASCII conversion and drawing (below) |
| `scene_eye.py` | the single-eye scene |

The ASCII conversion splits every character cell into 2×3 sub-cells and picks the glyph whose shape, measured from the real font, best matches both the density and the pattern of those six values. That is why lash lines and hair strands keep their direction.

Drawing keeps the frame in a NumPy buffer and sends only changed rectangles to the window with `XPutImage`; Tk photo images are the fallback.

## Credits

- The `eye` scene's ASCII eye (`assets/eye.json`) and the idle routine come from the profile card in [hdnng/hdnng](https://github.com/hdnng/hdnng).
- `assets/avatar.png` is the author's GitHub avatar. To make the wallpaper your own, swap in your own picture as described above.
