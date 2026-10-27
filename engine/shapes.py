"""أشكال مصقولة (anti-aliased) ودوال لصق وتدرجات وإيقاعات حركة."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 2


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def clamp01(t):
    return 0.0 if t < 0 else 1.0 if t > 1 else t


def ease_out_cubic(t):
    t = clamp01(t)
    return 1 - (1 - t) ** 3


def ease_out_back(t, k=1.70158):
    t = clamp01(t) - 1
    return 1 + (k + 1) * t ** 3 + k * t ** 2


class AA:
    """لوحة رسم بدقة مضاعفة ثم تصغير لحواف ناعمة."""

    def __init__(self, w, h):
        self.w, self.h = int(w), int(h)
        self.img = Image.new("RGBA", (self.w * SS, self.h * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def _s(self, b):
        flat = [c for v in b for c in (v if isinstance(v, (tuple, list)) else (v,))]
        return [v * SS for v in flat]

    def rrect(self, box, r, fill=None, outline=None, width=0):
        self.d.rounded_rectangle(self._s(box), radius=r * SS, fill=fill, outline=outline, width=int(width * SS))

    def ellipse(self, box, fill=None, outline=None, width=0):
        self.d.ellipse(self._s(box), fill=fill, outline=outline, width=int(width * SS))

    def line(self, pts, fill, width):
        self.d.line(self._s(pts), fill=fill, width=int(width * SS), joint="curve")

    def arc(self, box, a0, a1, fill, width):
        self.d.arc(self._s(box), a0, a1, fill=fill, width=int(width * SS))

    def done(self):
        return self.img.resize((self.w, self.h), Image.LANCZOS)


def with_shadow(spr, blur=20, offset=(0, 12), alpha=80):
    pad = int(blur * 2 + max(abs(offset[0]), abs(offset[1])) + 2)
    out = Image.new("RGBA", (spr.width + 2 * pad, spr.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    mask = spr.getchannel("A").point(lambda v: v * alpha // 255)
    sh.paste((0, 0, 0, 255), (pad + int(offset[0]), pad + int(offset[1])), mask)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(sh)
    out.alpha_composite(spr, (pad, pad))
    return out


def circle(d, color, shadow=True):
    a = AA(d, d)
    a.ellipse((0, 0, d - 1, d - 1), fill=tuple(color) + (255,))
    s = a.done()
    return with_shadow(s, blur=d * 0.035, offset=(0, d * 0.03), alpha=70) if shadow else s


def dot(size, color):
    """نقطة متوهجة ناعمة للجسيمات."""
    n = int(size * 4)
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot(x - n / 2, y - n / 2) / (n / 2)
    a = np.clip(1 - r, 0, 1) ** 1.6
    arr = np.zeros((n, n, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = color
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def paste_center(cv, spr, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0.01 or scale <= 0.01:
        return
    if abs(scale - 1) > 1e-3:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if alpha < 0.99:
        a = spr.getchannel("A").point(lambda v: int(v * alpha))
        spr = spr.copy()
        spr.putalpha(a)
    cv.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)


def gradient(W, H, c1, c2, mode="v"):
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    x = np.linspace(0, 1, W, dtype=np.float32)[None, :]
    t = y if mode == "v" else (x * 0.45 + y * 0.55)
    t = np.broadcast_to(t, (H, W))[..., None]
    arr = np.array(c1, np.float32) * (1 - t) + np.array(c2, np.float32) * t
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def radial(W, H, cx, cy, r, inner, outer):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    t = np.clip(np.hypot(x - cx, y - cy) / r, 0, 1)[..., None] ** 1.4
    arr = np.array(inner, np.float32) * (1 - t) + np.array(outer, np.float32) * t
    return Image.fromarray(arr.astype(np.uint8), "RGB")
