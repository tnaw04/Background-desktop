#!/usr/bin/env python3
"""Export the automatic ASCII face as a seamless-size GNOME wallpaper video."""

import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from behaviour import Behaviour, EYE_T
from eyes import DEFAULTS, ROOT, THEMES, find_font
from scene_face import FaceScene, mix


class FrameCanvas:
    """Draw the scene's glyph and palette grids into an RGB frame."""

    def __init__(self, frame, glyph_set, rows, cols, x, y, background, palette):
        self.pixels = frame[y:y + rows * glyph_set.ch, x:x + cols * glyph_set.cw]
        coverage = glyph_set.atlas[None, :, :, :, None] / 255
        bg = np.asarray(background, dtype=float)
        colors = np.asarray(palette, dtype=float)[:, None, None, None, :]
        self.atlas = np.rint(bg + coverage * (colors - bg)).astype(np.uint8)

    def show(self, glyphs, colors):
        self.pixels[:] = self.atlas[colors, glyphs].transpose(0, 2, 1, 3, 4).reshape(self.pixels.shape)


class WallpaperFrames:
    def __init__(self, width, height):
        config = dict(DEFAULTS)
        config.update(json.loads((ROOT / "config.json").read_text()))
        config.update(fit="contain", face_size=1.0, position=[0.5, 0.5])
        config["effects"] = dict.fromkeys(("water", "ripples", "hair", "stars", "glow"), False)
        colors = dict(THEMES[config["theme"]])
        colors["bg"] = config["background"] or colors["bg"]
        font = config["font"] or find_font()
        if not font:
            raise ValueError("Install a monospace font or set font in config.json.")

        self.width, self.height = width, height
        self.pixels = np.empty((height, width, 3), dtype=np.uint8)
        self.scene = FaceScene(config, colors, font, self.pixels, canvas_factory=FrameCanvas)
        self.scene.layout(dict(x=0, y=0, w=width, h=height))
        self.pixels[:] = self.scene.bg
        if self.scene.width == self.scene.height:
            self.draw_digits(font)
        self.behaviour = Behaviour(0, 0)
        self.previous_time = 0

    def draw_digits(self, font_path):
        scene = self.scene
        image = Image.new("RGB", (self.width, self.height), scene.bg)
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(font_path, max(6, round(scene.gs.cw / 0.602)))
        left = scene.origin[0]
        right = left + scene.cols * scene.gs.cw
        random = np.random.default_rng(42)
        for start, end, inner_edge in ((0, left, left), (right, self.width, right)):
            for x in range(start + scene.gs.cw // 2, end, scene.gs.cw):
                depth = min(abs(x - inner_edge) / max(1, (end - start) * 0.4), 1)
                for y in range(scene.gs.ch // 2, self.height, scene.gs.ch):
                    if random.random() < 0.18:
                        continue
                    brightness = depth * random.uniform(0.13, 0.44)
                    color = mix(scene.bg, scene.palette[0], brightness)
                    draw.text((x, y), str(random.integers(10)), fill=color, font=font, anchor="mm")
        self.pixels[:] = image

    def frame(self, time):
        dt = min(max(time - self.previous_time, 0), 0.1)
        self.previous_time = time
        self.behaviour.update(time, dt, None, (self.width, self.height), self.scene.focus)
        self.scene.frame(time, dt, self.behaviour)
        return self.pixels

    def motion_box(self):
        x, y = self.scene.origin
        cw, ch = self.scene.gs.cw, self.scene.gs.ch
        rows, cols = zip(*self.scene.eye_cells)
        return (
            x + min(col.start for col in cols) * cw,
            y + min(row.start for row in rows) * ch,
            x + max(col.stop for col in cols) * cw,
            y + max(row.stop for row in rows) * ch,
        )


def encode(output, width, height, fps, seconds, assets=None):
    frames = WallpaperFrames(width, height)
    count = math.ceil(seconds * fps)
    if assets is not None:
        assets.mkdir(parents=True, exist_ok=True)
        x0, y0, x1, y1 = frames.motion_box()
        info = dict(width=width, height=height, fps=fps, count=count,
                    patch=[x0, y0, x1 - x0, y1 - y0])
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as directory:
        video = Path(directory) / "wallpaper.webm"
        pipeline = [
            "gst-launch-1.0", "-q", "fdsrc", "fd=0", "!", "rawvideoparse",
            "format=rgb", f"width={width}", f"height={height}", f"framerate={fps}/1",
            "!", "videoconvert", "!", "vp8enc", "deadline=1", "target-bitrate=8500000",
            "keyframe-max-dist=24", "!", "webmmux", "!", "filesink", f"location={video}",
        ]
        with subprocess.Popen(pipeline, stdin=subprocess.PIPE) as process:
            for index in range(count):
                frame = frames.frame(index / fps)
                process.stdin.write(frame.tobytes())
                if assets is not None:
                    if index == 0:
                        Image.fromarray(frame).save(assets / "backdrop.png")
                    Image.fromarray(frame[y0:y1, x0:x1]).save(assets / f"frame-{index}.png")
            process.stdin.close()
            if process.wait() or not video.is_file() or not video.stat().st_size:
                raise RuntimeError("GStreamer did not write the wallpaper video.")
        os.replace(video, output)
    if assets is not None:
        (assets / "frames.json").write_text(json.dumps(info))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1200)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--seconds", type=float, default=EYE_T)
    parser.add_argument("--assets", type=Path, help="Also export lightweight GNOME playback frames.")
    args = parser.parse_args()
    if (min(args.width, args.height) < 64 or args.width % 4 or args.height % 2
            or args.fps < 1 or not math.isfinite(args.seconds) or args.seconds <= 0):
        parser.error("Use even dimensions of at least 64 px, width divisible by four, and positive timing.")
    encode(args.output, args.width, args.height, args.fps, args.seconds, args.assets)


if __name__ == "__main__":
    main()
