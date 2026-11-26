"""Scene 'face': the GitHub avatar redrawn in ASCII, alive, filling the screen.

Every frame the avatar is resampled through a displacement field and turned into glyphs:

  eyes      each eyeball is painted afresh: shaded white with the upper lid's shadow, an iris
            built from the drawing's own iris (re-mapped in polar coordinates so the pupil can
            widen) plus fine radial fibres, a dark limbal ring and catchlights. The iris slides
            behind the real lid lines, foreshortens towards the corners, and the upper lid
            slides down with its lashes to squint and blink
  hair      strands sway along their own direction, tips more than roots, in gusts; moving
            the pointer through the hair brushes it aside and it springs back
  water     the water sways, and rings spread from clicks and from the pointer gliding over it
  stars     the white specks in the hair twinkle
  light     a soft glow follows the pointer

Geometry (lid curves, iris, hair regions, water line) is in avatar pixels in assets/face.json.
"""
import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from ascii_render import GlyphSet, make_canvas, dither_for, SUB_X, SUB_Y
from behaviour import Follower

ROOT = Path(__file__).resolve().parent
UP = 2                              # the avatar is upscaled this much before sampling


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def prepare(path):
    """The avatar, upscaled, tones spread out and lines sharpened, as floats 0..1."""
    im = ImageOps.equalize(Image.open(path).convert("L"))
    im = im.resize((im.width * UP, im.height * UP), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=12, percent=170, threshold=0))
    a = np.asarray(im, np.float32) / 255
    lo, hi = np.percentile(a, [1, 99])
    return np.clip((a - lo) / (hi - lo), 0, 1)


def find_stars(path, bottom, limit):
    """Small bright specks on dark ground in the hair: (x, y) in avatar px."""
    a = np.asarray(Image.open(path).convert("L"), np.float32) / 255
    local = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(5)), np.float32) / 255
    score = (a - local) * (a > 0.6)
    score[bottom:] = 0
    stars = []
    for _ in range(limit):
        y, x = np.unravel_index(score.argmax(), score.shape)
        if score[y, x] < 0.25:
            break
        stars.append((int(x), int(y)))
        score[max(0, y - 10):y + 11, max(0, x - 10):x + 11] = 0
    return stars


def _bilinear(img, X, Y):
    h, w = img.shape
    X = np.clip(X, 0, w - 1.001)
    Y = np.clip(Y, 0, h - 1.001)
    x0, y0 = X.astype(np.int32), Y.astype(np.int32)
    fx, fy = X - x0, Y - y0
    a, b = img[y0, x0], img[y0, x0 + 1]
    c, d = img[y0 + 1, x0], img[y0 + 1, x0 + 1]
    return (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy


def sample(img, X, Y):
    """Bilinear sample of the (upscaled) avatar at avatar-px coordinates."""
    return _bilinear(img, X * UP + (UP - 1) / 2, Y * UP + (UP - 1) / 2)


def sample_plain(img, X, Y):
    """Bilinear sample of an avatar-sized array (no upscale)."""
    return _bilinear(img, X, Y)


class Eye:
    """One eye's geometry from face.json, in avatar px."""

    def __init__(self, g, src):
        self.ux, self.uy = (np.array(v, np.float32) for v in zip(*g["upper"]))
        self.lx, self.ly = (np.array(v, np.float32) for v in zip(*g["lower"]))
        self.xl, self.xr = float(self.ux[0]), float(self.ux[-1])
        (x0, y0), (x1, y1) = g["upper"][0], g["upper"][-1]
        self.theta = math.atan2(y1 - y0, x1 - x0)
        self.cos, self.sin = math.cos(self.theta), math.sin(self.theta)
        self.cx, self.cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.half = math.hypot(x1 - x0, y1 - y0) / 2
        self.ix, self.iy, self.r = g["iris"]
        lid = g.get("lid", {})
        self.lash, self.skin_h = float(lid.get("lash", 8)), float(lid.get("skin", 10))
        # tones of the drawing's own white and iris, so the painted eye matches its surroundings
        last_x = int(min(self.xr, src.shape[1] // UP - 1))
        pts = [(x, y) for x in range(int(self.xl), last_x)
               for y in range(int(self.top(x)) + 2, int(self.bottom(x)) - 1)]
        self.sclera, self.iris_lo, self.iris_hi = 0.85, 0.15, 0.55
        # the skin just under the lower lid gives the closed lid its tone
        sk = [(x, y) for x in range(int(self.xl) + 4, last_x - 4, 2)
              for y in range(int(self.bottom(x)) + 4, int(self.bottom(x)) + 14, 2)]
        self.skin = float(np.percentile(sample(src, *np.array(sk, np.float32).T), 60)) if sk else 0.6
        if pts:
            px, py = np.array(pts, np.float32).T
            v = sample(src, px, py)
            d2 = (px - self.ix) ** 2 + (py - self.iy) ** 2
            iris, out = d2 < (self.r * 0.9) ** 2, d2 > (self.r * 1.25) ** 2
            if out.any():
                self.sclera = float(np.percentile(v[out], 75))
            if iris.any():
                self.iris_lo = float(np.percentile(v[iris], 10))
                self.iris_hi = float(np.percentile(v[iris], 90))

    def top(self, x):
        return np.interp(x, self.ux, self.uy)

    def bottom(self, x):
        return np.interp(x, self.lx, self.ly)


class FaceScene:
    def __init__(self, cfg, colors, font, canvas, *, canvas_factory=make_canvas):
        self.cfg, self.font, self.canvas = cfg, font, canvas
        self.canvas_factory = canvas_factory
        self.geo = json.loads((ROOT / "assets" / "face.json").read_text())
        src_path = ROOT / "assets" / self.geo["source"]
        self.src = prepare(src_path)
        self.height, self.width = (dimension // UP for dimension in self.src.shape)
        self.light = cfg["theme"] == "light"
        self.fx = dict(dict(water=True, ripples=True, hair=True, stars=True, glow=True), **cfg.get("effects", {}))
        self.hair_strength = float(cfg.get("hair_strength", 3.5))
        st = self.geo["stars"]
        self.stars = find_stars(src_path, st["bottom"], st["max"]) if self.fx["stars"] else []
        self.eyes = [Eye(g, self.src) for g in self.geo["eyes"]]
        self.follow = [Follower() for _ in self.eyes]
        self.ripples, self.brushes = [], []
        self.last_wake = self.last_brush = 0.0
        self.prev_ptr = None

        # hair: a soft mask per region, with the direction its strands run (root -> tip)
        self.hair = []
        for h in self.geo.get("hair", []):
            m = Image.new("L", (self.width, self.height), 0)
            ImageDraw.Draw(m).polygon([tuple(p) for p in h["polygon"]], fill=255)
            m = np.asarray(m.filter(ImageFilter.GaussianBlur(6)), np.float32) / 255
            d = np.array(h["direction"], np.float32)
            d /= np.linalg.norm(d)
            self.hair.append(dict(mask=m, root=np.array(h["root"], np.float32), t=d,
                                  n=np.array([-d[1], d[0]], np.float32), reach=float(h.get("reach", 300))))
        self.hair_any = sum((h["mask"] for h in self.hair),
                            np.zeros((self.height, self.width), np.float32)).clip(0, 1)

        # tone curve as a lookup table: an S-curve for contrast around the skin's mid greys
        x = np.linspace(0, 1, 256, dtype=np.float32)
        sig = lambda v: 1 / (1 + np.exp(-7 * (v - 0.5)))
        sc = lambda v: (sig(v) - sig(0)) / (sig(1) - sig(0))
        self.tone = (sc(1 - x) ** 1.1 if self.light else sc(x) ** 1.3).astype(np.float32)

        bg, art, value = rgb(colors["bg"]), rgb(colors["art"]), rgb(colors["value"])
        hi = (255, 255, 255) if not self.light else rgb("#0969da")
        # colour ids: 0 art, 1 iris, 2-4 pointer glow, 5 sparkle (stars, catchlights)
        self.bg = bg
        self.palette = [art, value, mix(art, hi, 0.25), mix(art, hi, 0.5), mix(art, hi, 0.75), hi]

    # ------------------------------------------------------------ layout
    def layout(self, mon):
        cfg, width, height = self.cfg, self.width, self.height
        cw = max(3, round(cfg.get("cell", 5) * mon["h"] / 1080))
        ch = 2 * cw
        fit = cfg.get("fit", "cover")
        if fit == "cover":                   # fill the whole monitor, cropping the avatar
            W, H = mon["w"], mon["h"]
            s = max(W / width, H / height)
            self.cols, self.rows = W // cw, H // ch
            gw, gh = self.cols * cw, self.rows * ch
            vw, vh = gw / s, gh / s
            fx, fy = cfg.get("focus") or self.geo.get("focus", [0.5, 0.5])
            vx = min(max(fx * width - vw / 2, 0), width - vw)
            vy = min(max(fy * height - vh / 2, 0), height - vh)
            ox, oy = mon["x"] + (W - gw) // 2, mon["y"] + (H - gh) // 2
        else:                                # the whole image, centred
            width_limit = mon["w"] * (0.96 if width == height else 1.0)
            height_limit = mon["h"] * min(cfg.get("face_size", 0.92), 1.0)
            s = min(width_limit / width, height_limit / height)
            self.cols = int(width * s // cw)
            self.rows = int(height * s // ch)
            gw, gh = self.cols * cw, self.rows * ch
            px, py = cfg["position"]
            ox = round(min(max(mon["x"] + px * mon["w"] - gw / 2, mon["x"]), mon["x"] + mon["w"] - gw))
            oy = round(min(max(mon["y"] + py * mon["h"] - gh / 2, mon["y"]), mon["y"] + mon["h"] - gh))
            vx, vy, vw, vh = 0.0, 0.0, float(width), float(height)
            s = gw / width
        self.view = (vx, vy, vw, vh)
        self.origin, self.scale = (ox, oy), s

        self.gs = GlyphSet(self.font, cw, ch)
        fh, fw = self.rows * SUB_Y, self.cols * SUB_X
        xs = vx + (np.arange(fw, dtype=np.float32) + 0.5) / fw * vw - 0.5
        ys = vy + (np.arange(fh, dtype=np.float32) + 0.5) / fh * vh - 0.5
        self.X0, self.Y0 = np.meshgrid(xs, ys)
        self.dither = dither_for((fh, fw)).astype(np.float32)
        if fit == "cover":                   # a gentle fade at the top and bottom edges
            e = np.minimum(np.arange(fh), fh - 1 - np.arange(fh)) / fh
            self.vignette = np.repeat((0.35 + 0.65 * smoothstep(0, 0.05, e))[:, None], fw, 1).astype(np.float32)
        elif width == height:               # fade the square's edges into the background
            u = np.minimum(xs, width - 1 - xs) / width
            v = np.minimum(ys, height - 1 - ys) / height
            self.vignette = (smoothstep(0.0, 0.07, v)[:, None] * smoothstep(0.0, 0.07, u)[None, :]).astype(np.float32)
        else:
            self.vignette = np.ones((fh, fw), np.float32)
        cx = vx + (np.arange(self.cols, dtype=np.float32) + 0.5) / self.cols * vw
        cy = vy + (np.arange(self.rows, dtype=np.float32) + 0.5) / self.rows * vh
        self.CX, self.CY = np.meshgrid(cx, cy)

        wat = self.geo["water"]
        self.water_r0 = int(np.searchsorted(ys, wat["top"]))
        self.water_w = smoothstep(wat["top"], wat["full"], self.Y0[self.water_r0:]).astype(np.float32)

        # hair: the rows it covers, and per region its weight and strand coordinates there
        self.hair_rows, self.hair_band = None, []
        if self.hair:
            rows = np.nonzero((sample_plain(self.hair_any, self.X0, self.Y0) > 0.01).any(1))[0]
            if len(rows):
                a, b = int(rows[0]), int(rows[-1]) + 1
                self.hair_rows = (a - a % SUB_Y, min(fh, b + (-b) % SUB_Y))
                hx = self.X0[self.hair_rows[0]:self.hair_rows[1]]
                hy = self.Y0[self.hair_rows[0]:self.hair_rows[1]]
                for h in self.hair:
                    m = sample_plain(h["mask"], hx, hy)
                    rr, cc = np.nonzero(m > 0.01)
                    if not len(rr):
                        continue
                    box = (slice(int(rr.min()), int(rr.max()) + 1), slice(int(cc.min()), int(cc.max()) + 1))
                    bx, by = hx[box], hy[box]          # only where this region has hair
                    along = (bx - h["root"][0]) * h["t"][0] + (by - h["root"][1]) * h["t"][1]
                    across = (bx - h["root"][0]) * h["n"][0] + (by - h["root"][1]) * h["n"][1]
                    ramp = smoothstep(0.05 * h["reach"], 0.85 * h["reach"], along)
                    self.hair_band.append((box, (m[box] * ramp).astype(np.float32),
                                           along.astype(np.float32), across.astype(np.float32), h))
                self.hair_m = sample_plain(self.hair_any, hx, hy)

        # per eye: a window of whole cells around it (cell slices and feature slices)
        self.eye_cells, self.eye_win = [], []
        for e in self.eyes:
            cells = self.cell_rect(e.xl - 3, float(e.uy.min()) - 16, e.xr + 3, float(e.ly.max()) + 3)
            self.eye_cells.append(cells)
            self.eye_win.append(self.feat(cells))
        self.star_cells, self.star_phase = [], []
        for x, y in self.stars:
            r, c = (y - vy) / vh * self.rows, (x - vx) / vw * self.cols
            if 0 <= r < self.rows and 0 <= c < self.cols:
                self.star_cells.append((int(r), int(c)))
                self.star_phase.append((random.uniform(0, 6.3), random.uniform(1.6, 4.5)))

        if getattr(self, "tiles", None) is not None and hasattr(self.tiles, "close"):
            self.tiles.close()
        self.tiles = self.canvas_factory(self.canvas, self.gs, self.rows, self.cols, ox, oy, self.bg, self.palette)
        self.eye_screen = [self.to_screen(e.ix, e.iy) for e in self.eyes]
        self.focus = self.to_screen(*np.mean([(e.ix, e.iy) for e in self.eyes], axis=0))

        # the still picture; animated row bands and the eyes are recomputed on top of it
        allw = (slice(None), slice(None))
        self.I0 = self.to_ink(sample(self.src, self.X0, self.Y0), allw)
        self.G0 = self.gs.glyphs(self.I0, self.dither)
        self.Xa, self.Ya = self.X0.copy(), self.Y0.copy()
        self.I, self.G = self.I0.copy(), self.G0.copy()
        self.bands, self.next_amb, self.last_sig = [], 0.0, None
        self.eye_cache = [None] * len(self.eyes)

    def cell_rect(self, x0, y0, x1, y1):
        """Cells covering an avatar-px rectangle, as (row slice, col slice)."""
        vx, vy, vw, vh = self.view
        r0 = max(0, int((y0 - vy) / vh * self.rows))
        r1 = min(self.rows, int(math.ceil((y1 - vy) / vh * self.rows)))
        c0 = max(0, int((x0 - vx) / vw * self.cols))
        c1 = min(self.cols, int(math.ceil((x1 - vx) / vw * self.cols)))
        return slice(r0, max(r0, r1)), slice(c0, max(c0, c1))

    @staticmethod
    def feat(cells):
        rs, cs = cells
        return slice(rs.start * SUB_Y, rs.stop * SUB_Y), slice(cs.start * SUB_X, cs.stop * SUB_X)

    def to_ink(self, B, win):
        return self.tone[(np.clip(B, 0, 1) * 255).astype(np.uint8)] * self.vignette[win]

    def to_src(self, x, y):
        vx, vy = self.view[:2]
        return vx + (x - self.origin[0]) / self.scale, vy + (y - self.origin[1]) / self.scale

    def to_screen(self, x, y):
        vx, vy = self.view[:2]
        return self.origin[0] + (x - vx) * self.scale, self.origin[1] + (y - vy) * self.scale

    def in_view(self, sx, sy):
        vx, vy, vw, vh = self.view
        return vx <= sx < vx + vw and vy <= sy < vy + vh

    # ------------------------------------------------------------ interaction
    def click(self, x, y, now):
        sx, sy = self.to_src(x, y)
        if self.in_view(sx, sy):
            self.ripples.append((sx, sy, now, 4.0))

    def pointer_effects(self, beh, now, dt):
        """Rings behind the pointer on the water; brushing the hair aside as it passes."""
        ptr, prev = beh.ptr, self.prev_ptr
        self.prev_ptr = ptr
        if not (beh.moved and ptr and prev and beh.on_desktop):
            return
        sx, sy = self.to_src(*ptr)
        if not self.in_view(sx, sy):
            return
        if self.fx["ripples"] and sy >= self.geo["water"]["top"] and now - self.last_wake >= 0.12:
            self.ripples.append((sx, sy, now, 1.6))
            self.last_wake = now
        if self.fx["hair"] and self.hair_rows and now - self.last_brush >= 0.05 \
                and sample_plain(self.hair_any, np.float32(sx), np.float32(sy)) > 0.15:
            px, py = self.to_src(*prev)
            vx, vy = (sx - px) / max(dt, 1e-3), (sy - py) / max(dt, 1e-3)
            if math.hypot(vx, vy) > 5:
                self.brushes.append((sx, sy, vx, vy, now))
                self.brushes = self.brushes[-16:]
                self.last_brush = now

    # ------------------------------------------------------------ the slow layer
    def ripple_rows(self, now):
        """(ripple, feature-row range it can touch) for every live ripple."""
        fh = self.X0.shape[0]
        vy, vh = self.view[1], self.view[3]
        for rip in self.ripples:
            rx, ry, t0, amp = rip
            age = now - t0
            radius, width = 55.0 * age, 14.0 + 6.0 * age
            ya = int(min(max((ry - radius - 2 * width - vy) / vh * fh, 0), fh))
            yb = int(min(max((ry + radius + 2 * width - vy) / vh * fh, 0), fh)) + 1
            yield rip, age, radius, width, ya, min(yb, fh)

    def ambient(self, now):
        """Hair, water and ripples, recomputed at the ambient rate and only for the row bands
        they touch. Returns the feature-row bands that changed."""
        fh = self.X0.shape[0]
        want = []
        if self.fx["hair"] and self.hair_rows:
            want.append(self.hair_rows)
        if self.fx["water"] and self.water_r0 < fh:
            want.append((self.water_r0, fh))
        rip = [r for r in self.ripple_rows(now) if r[4] < r[5]]
        want += [(r[4], r[5]) for r in rip]
        want = sorted((a - a % SUB_Y, min(fh, b + (-b) % SUB_Y)) for a, b in want)
        bands = []
        for a, b in want:
            if bands and a <= bands[-1][1]:
                bands[-1] = (bands[-1][0], max(bands[-1][1], b))
            else:
                bands.append((a, b))
        # rows animated last time but not now go back to the still picture
        dirty = list(bands)
        for a, b in self.bands:
            covered = np.zeros(b - a, bool)
            for c, d in bands:
                lo, hi = max(a, c), min(b, d)
                if lo < hi:
                    covered[lo - a:hi - a] = True
            if not covered.all():
                idx = np.nonzero(~covered)[0] + a
                self.Xa[idx], self.Ya[idx] = self.X0[idx], self.Y0[idx]
                self.I[idx] = self.I0[idx]
                rows = np.unique(idx // SUB_Y)
                self.G[rows] = self.G0[rows]
                dirty.append((int(idx.min()), int(idx.max()) + 1))
        self.bands = bands

        t = now
        self.brushes = [b for b in self.brushes if now - b[4] < 1.6]
        for a, b in bands:
            X, Y = self.X0[a:b].copy(), self.Y0[a:b].copy()
            shade = np.zeros_like(X)                  # light and shadow on the water's surface
            lo = max(a, self.water_r0)
            if self.fx["water"] and lo < b:
                sl = slice(lo - a, b - a)
                wy, wx = self.Y0[lo:b], self.X0[lo:b]
                w = self.water_w[lo - self.water_r0:b - self.water_r0]
                X[sl] += w * (0.8 * np.sin(0.09 * wy + 1.3 * t) + 0.5 * np.sin(0.05 * wy - 0.04 * wx + 0.8 * t))
                Y[sl] += w * 0.5 * np.sin(0.07 * wx + 1.1 * t)
                shade[sl] += w * 0.07 * np.sin(0.11 * wy - 0.03 * wx + 1.7 * t) * np.sin(0.05 * wx + 0.6 * t)
            for (rx, ry, t0, amp), age, radius, width, ya, yb in rip:
                lo, hi = max(a, ya), min(b, yb)
                if lo >= hi:
                    continue
                dx, dy = self.X0[lo:hi] - rx, self.Y0[lo:hi] - ry
                dist = np.sqrt(dx * dx + dy * dy) + 1e-3
                off = dist - radius
                wave = amp * math.exp(-1.2 * age) * np.sin(0.35 * off) * np.exp(-(off / width) ** 2)
                if self.water_r0 > lo:              # calmer outside the water
                    wave[:self.water_r0 - lo] *= 0.3
                X[lo - a:hi - a] += wave * dx / dist
                Y[lo - a:hi - a] += wave * dy / dist
                shade[lo - a:hi - a] -= 0.09 * wave       # dark troughs, bright crests
            if self.fx["hair"] and self.hair_rows:
                ha, hb = self.hair_rows
                lo, hi = max(a, ha), min(b, hb)
                if lo < hi:
                    dx, dy = self.hair_motion(t, now, lo - ha, hi - ha)
                    X[lo - a:hi - a] -= dx                # sample from behind: the hair moves by +d
                    Y[lo - a:hi - a] -= dy
            self.Xa[a:b], self.Ya[a:b] = X, Y
            win = (slice(a, b), slice(None))
            self.I[a:b] = self.to_ink(sample(self.src, X, Y) + shade, win)
            self.G[a // SUB_Y:b // SUB_Y] = self.gs.glyphs(self.I[a:b], self.dither[a:b])
        return dirty, rip

    def hair_motion(self, t, now, r0, r1):
        """How far each hair point is carried (dx, dy in avatar px), for hair-band rows r0:r1."""
        A = self.hair_strength
        gust = 0.6 * math.sin(0.33 * t) * math.sin(0.21 * t + 0.8) + 0.25 * math.sin(0.97 * t + 0.4)
        shape = (r1 - r0, self.X0.shape[1])
        dx, dy = np.zeros(shape, np.float32), np.zeros(shape, np.float32)
        for (rs, cs), w, along, across, h in self.hair_band:
            a, b = max(r0, rs.start), min(r1, rs.stop)          # this region's rows within r0:r1
            if a >= b:
                continue
            k = slice(a - rs.start, b - rs.start)
            w, along, across = w[k], along[k], across[k]
            # sideways sway: two waves travelling down the strands, shifted from strand to strand
            side = A * w * (0.55 * np.sin(0.045 * along - 1.7 * t + 0.06 * across)
                            + 0.25 * np.sin(0.11 * along - 2.6 * t + 0.15 * across + 1.3) + 0.8 * gust)
            slide = 0.35 * A * w * np.sin(0.03 * along - 1.2 * t + 0.05 * across)
            dx[a - r0:b - r0, cs] += side * h["n"][0] + slide * h["t"][0]
            dy[a - r0:b - r0, cs] += side * h["n"][1] + slide * h["t"][1]
        if self.brushes:
            ha = self.hair_rows[0]
            hx, hy = self.X0[ha + r0:ha + r1], self.Y0[ha + r0:ha + r1]
            m = self.hair_m[r0:r1]
            for (bx, by, vx, vy, t0) in self.brushes:
                age = now - t0
                sp = math.hypot(vx, vy)
                k = min(sp * 0.012, 4.5) * math.exp(-2.2 * age) * math.cos(7.0 * age)  # springs back
                g = np.exp(-((hx - bx) ** 2 + (hy - by) ** 2) / (2 * 28.0 ** 2)) * m
                dx = dx + g * k * vx / sp
                dy = dy + g * k * vy / sp
        return dx, dy

    # ------------------------------------------------------------ one frame
    def frame(self, now, dt, beh):
        self.pointer_effects(beh, now, dt)
        self.ripples = [r for r in self.ripples if now - r[2] < 3.0][-24:]
        changed = False
        if now >= self.next_amb:
            dirty, rip = self.ambient(now)
            rate = self.cfg.get("ambient_fps", 12)
            self.next_amb = now + 1.0 / (max(rate, 20) if self.ripples else rate)
            for k, (ws, cs) in enumerate(self.eye_win):
                cache = self.eye_cache[k]
                if cache is None or not any(a < ws.stop and ws.start < b for a, b in dirty):
                    continue
                if any(r[4] < ws.stop and ws.start < r[5] for r in rip):
                    self.eye_cache[k] = None           # a ripple crosses this eye: repaint it
                else:                                  # only overwritten: put the painted eye back
                    self.I[ws, cs] = cache[1]
                    self.G[self.eye_cells[k]] = cache[2]
            changed = bool(dirty)

        for k, (e, win, cells) in enumerate(zip(self.eyes, self.eye_win, self.eye_cells)):
            tx, ty, squint = beh.target(self.eye_screen[k], e.theta)
            nx, ny = self.follow[k].step((tx, ty), dt, beh.jit)
            c = beh.lid(squint, ny, now)
            key = (round(nx * 60), round(ny * 40), round(c * 40), round(beh.pupil * 40))
            cache = self.eye_cache[k]
            if cache is not None and cache[0] == key:
                continue
            B, cls = self.paint_eye(e, self.Xa[win], self.Ya[win], nx, ny, c, beh.pupil)
            self.I[win] = self.to_ink(B, win)
            self.G[cells] = self.gs.glyphs(self.I[win], self.dither[win])
            r, w = cls.shape[0] // SUB_Y, cls.shape[1] // SUB_X
            blocks = cls.reshape(r, SUB_Y, w, SUB_X)
            cell_cls = np.where((blocks == 2).any(axis=(1, 3)), 5,
                                np.where((blocks == 1).mean(axis=(1, 3)) > 0.5, 1, 0)).astype(np.uint8)
            self.eye_cache[k] = (key, self.I[win].copy(), self.G[cells].copy(), cell_cls)
            changed = True

        glow_key = None
        if self.fx["glow"] and beh.ptr is not None and beh.on_desktop:
            sx, sy = self.to_src(*beh.ptr)
            R = 0.22 * self.view[3]
            vx, vy, vw, vh = self.view
            if vx - R < sx < vx + vw + R and vy - R < sy < vy + vh + R:
                glow_key = (round(sx * 2), round(sy * 2))
        star_key = tuple(self.star_level(now, ph, per) for ph, per in self.star_phase)
        sig = (glow_key, star_key)
        if not changed and sig == self.last_sig:
            return                                   # nothing visible changed
        self.last_sig = sig

        glyphs = self.G.copy()
        colors = np.zeros((self.rows, self.cols), np.uint8)
        for cells, cache in zip(self.eye_cells, self.eye_cache):
            if cache is not None:
                sub, cc = colors[cells], cache[3]
                sub[cc > 0] = cc[cc > 0]
        if glow_key is not None:
            self.glow(beh.ptr, glyphs, colors)
        self.twinkle(star_key, glyphs, colors)
        self.tiles.show(glyphs, colors)

    # ------------------------------------------------------------ the eyes
    def paint_eye(self, e, X, Y, nx, ny, c, pupil):
        """Paint one eye window. Returns (brightness, class) arrays: class 1 iris, 2 catchlight."""
        src = self.src
        T, Bt = e.top(X), e.bottom(X)
        inx = (X > e.xl) & (X < e.xr)
        Hh = np.maximum(Bt - T, 0)
        ylid = T + c * Hh                                   # the upper lid's rim, now
        Y_src = Y
        if c > 0.01:
            # the lid slides down: its lash line (the dark band just above the opening) moves
            # with the rim, and the skin above the lashes stretches to cover the rest
            LB, SK = e.lash, e.skin_h                       # lash band, skin taken above it
            shift = c * Hh
            top_skin = T - LB - SK
            z = inx & (Y > top_skin) & (Y < ylid)
            lashes = Y >= ylid - LB
            skin = top_skin + (Y - top_skin) * SK / np.maximum(ylid - LB - top_skin, 1e-3)
            Y_src = np.where(z, np.where(lashes, Y - shift, skin), Y)
            lid_skin = z & ~lashes & (Y > T - LB)            # the part of the lid now over the eye
        out = sample(src, X, Y_src)
        if c > 0.01:                                         # lid skin in the skin's own tone
            out = np.where(lid_skin, 0.6 * max(e.skin, 0.55) + 0.4 * out, out)
        cls = np.zeros(X.shape, np.uint8)
        open_ = inx & (Y >= ylid) & (Y <= Bt) & (Hh > 0.5)
        if not open_.any():
            return out, cls

        x, y = X[open_], Y[open_]
        top, bot = ylid[open_], Bt[open_]
        h = np.maximum(bot - top, 1e-3)
        dtop, dbot = y - top, bot - y
        co, si = e.cos, e.sin
        # where the iris is now: slid along the eye's axes, squeezed as the eyeball turns
        gu = nx * (e.half - e.r) * 0.85
        gv = ny * e.r * 0.45
        mx, my = e.ix + gu * co - gv * si, e.iy + gu * si + gv * co
        f = float(np.clip(math.sqrt(max(0.0, 1 - (gu / (e.half * 1.05)) ** 2)), 0.62, 1.0))
        du, dv = x - mx, y - my
        lu = (du * co + dv * si) / f
        lv = -du * si + dv * co
        rho = np.sqrt(lu * lu + lv * lv)

        # the white: rounder in the middle, darker into the corners
        uc = (x - e.cx) * co + (y - e.cy) * si
        S = e.sclera * (0.8 + 0.2 * np.sin(np.pi * np.clip(dtop / h, 0, 1))) \
            * (0.78 + 0.22 * np.clip(1 - (uc / e.half) ** 2, 0, 1))
        val = S.copy()
        cz = np.zeros(x.shape, np.uint8)
        r = e.r
        iz = rho < r + 1.0
        if iz.any():
            rr, ph = rho[iz], np.arctan2(lv[iz], lu[iz])
            rp = r * 0.36 * pupil
            t = np.clip((rr - rp) / (r - rp), 0, 1)
            # the drawing's own iris, unwrapped around its centre so the pupil can change size
            ro = r * 0.36 + t * r * 0.64
            ca, sa = np.cos(ph), np.sin(ph)
            sx = e.ix + ro * (ca * co - sa * si)
            sy = e.iy + ro * (ca * si + sa * co)
            hidden = (sy < e.top(sx) + 1.5) | (sy > e.bottom(sx) - 1.5)   # under a lid in the drawing:
            sx = np.where(hidden, e.ix + ro * (ca * co + sa * si), sx)      # take the mirrored side
            sy = np.where(hidden, e.iy + ro * (ca * si - sa * co), sy)
            O = np.clip((sample(src, sx, sy) - e.iris_lo) / (e.iris_hi - e.iris_lo + 1e-3), 0, 1)
            fib = 0.5 + 0.25 * np.sin(ph * 34 + 2.5 * np.sin(ph * 7) + t * 3.0) \
                + 0.25 * np.sin(ph * 71 + 1.7 + 6.0 * t)
            # kept in the mid tones so the fibres show as glyphs in both themes
            iv = 0.3 + 0.62 * (0.4 * O + 0.6 * fib * (0.55 + 0.45 * t))
            iv = iv + 0.14 * np.exp(-((t - 0.33) / 0.07) ** 2)        # collarette
            iv = iv * (1 - 0.6 * smoothstep(0.8, 1.0, t))               # dark limbal ring
            iv = iv * (0.5 + 0.5 * smoothstep(0.0, 0.12, t))            # pupil rim
            iv = np.where(rr < rp, 0.02, iv)                            # pupil
            a = smoothstep(r - 0.7, r + 0.5, rr)
            val[iz] = iv * (1 - a) + S[iz] * a
            cz[np.nonzero(iz)[0][rr < r]] = 1
        val = val * (0.5 + 0.5 * smoothstep(0, 0.35 * h + 1, dtop))     # shadow of the upper lid

        # catchlights: reflections of a window, lagging behind the iris
        gx, gy = e.ix + 0.7 * (mx - e.ix), e.iy + 0.7 * (my - e.iy)
        win = ((x - (gx - 0.34 * r)) / (0.15 * r)) ** 2 + ((y - (gy - 0.30 * r)) / (0.11 * r)) ** 2 < 1
        dot = (x - (gx + 0.30 * r)) ** 2 + (y - (gy + 0.24 * r)) ** 2 < (0.07 * r) ** 2
        shine = (win | dot) & (rho < r)
        val = np.where(win & shine, 1.0, np.where(dot & shine, 0.92, val))
        cz[shine] = 2

        # blend into the drawn lid lines at the edges of the opening
        w = smoothstep(0, 1.6, dtop) * smoothstep(0, 1.6, dbot) \
            * smoothstep(0, 3.0, np.minimum(x - e.xl, e.xr - x))
        border = np.where(dtop < dbot, sample(src, x, y - c * Hh[open_]), out[open_])
        out[open_] = border + (val - border) * w
        cls[open_] = cz
        return out, cls

    # ------------------------------------------------------------ light and sparkle
    def glow(self, ptr, glyphs, colors):
        """A soft light around the pointer: denser glyphs and brighter colours nearby."""
        sx, sy = self.to_src(*ptr)
        R = 0.22 * self.view[3]
        cells = self.cell_rect(sx - R, sy - R, sx + R, sy + R)
        if cells[0].start >= cells[0].stop or cells[1].start >= cells[1].stop:
            return
        win = self.feat(cells)
        d2 = ((self.X0[win] - sx) ** 2 + (self.Y0[win] - sy) ** 2) / (R * R)
        g = np.clip(1 - d2, 0, 1) ** 2
        ink = self.I[win]
        ink = ink + (1 - ink) * 0.3 * g * self.vignette[win]
        glyphs[cells] = self.gs.glyphs(ink, self.dither[win])
        cg = np.clip(1 - ((self.CX[cells] - sx) ** 2 + (self.CY[cells] - sy) ** 2) / (R * R), 0, 1) ** 2
        lvl = np.digitize(cg, [0.12, 0.35, 0.65])          # 0..3
        sub = colors[cells]
        pick = (sub == 0) & (lvl > 0)
        sub[pick] = (1 + lvl[pick]).astype(np.uint8)

    @staticmethod
    def star_level(now, ph, per):
        s = math.sin(now * 2 * math.pi / per + ph)
        return 2 if s > 0.85 else 1 if s > 0.55 else 0

    def twinkle(self, levels, glyphs, colors):
        gi = self.gs.index
        for (r, c), lv in zip(self.star_cells, levels):
            if not lv:
                continue
            glyphs[r, c] = gi["*"] if lv == 2 else gi["+"]
            colors[r, c] = 5
            if lv == 2:                                     # little cross arms at full shine
                for cc in (c - 1, c + 1):
                    if 0 <= cc < self.cols:
                        glyphs[r, cc] = gi["-"]
                        colors[r, cc] = 5
