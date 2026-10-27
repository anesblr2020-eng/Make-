"""الستايلات الخمسة. كل ستايل يرسم الإطار حسب الزمن t والمشهد الحالي."""
import json
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw
from .fonts import get_font
from .shapes import (AA, circle, dot, ease_out_back, ease_out_cubic, gradient, hex2rgb,
                     paste_center, radial, with_shadow)
from .textlayout import build_words, draw_words

ROOT = Path(__file__).resolve().parent.parent
PRESETS = json.loads((ROOT / "styles" / "presets.json").read_text(encoding="utf-8"))["presets"]


class Style:
    key = ""
    max_words = 4
    anim = "pop"

    def __init__(self, W, H, o):
        self.W, self.H, self.S, self.o = W, H, W / 1080, o or {}
        self.pal = {k: hex2rgb(v) for k, v in PRESETS[self.key]["palette"].items()}

    def release(self, sc):
        sc.pop("_p", None)

    def words(self, sc, t, last, cv, **kw):
        draw_words(cv, sc["_p"]["items"], t, sc["text_end"], last, self.anim, self.S, **kw)


# ───────────────────────── 1) تحريري ليموني ─────────────────────────
class Editorial(Style):
    key = "editorial_lime"
    max_words = 4

    def __init__(self, W, H, o):
        super().__init__(W, H, o)
        self.lime = self.pal["accent"]
        self.bg = gradient(W, H, (246, 246, 246), (184, 184, 184), "d")

    def prepare(self, sc):
        W, H, S, i = self.W, self.H, self.S, sc["idx"]
        kind = i % 3
        cfg = dict(latin="Anton-Regular.ttf", arabic="Tajawal-Black.ttf", base=170, emph_scale=1.0,
                   color=(17, 17, 17), emph_color=(17, 17, 17), emph_box=self.lime, emph_text=(17, 17, 17),
                   shadow=None, cy=0.5 if kind != 2 else 0.42, max_w=0.84, max_lines=3, line_gap=1.0, upper=False)
        items, _ = build_words(sc, W, H, cfg)
        shapes = []
        if kind == 0:
            shapes.append((circle(int(0.68 * W), self.lime), (0.5 * W, 0.5 * H)))
        elif kind == 1:
            a = AA(int(0.34 * W), int(1.05 * H))
            a.rrect((0, 0, a.w - 1, a.h - 1), 10, fill=tuple(self.lime) + (255,))
            slab = with_shadow(a.done().rotate(-7, expand=True, resample=Image.BICUBIC), blur=22 * S, offset=(8, 10), alpha=60)
            shapes.append((slab, (0.26 * W, 0.5 * H)))
        else:
            shapes.append((circle(int(0.46 * W), self.lime), (0.3 * W, 0.74 * H)))
            shapes.append((circle(int(0.12 * W), (30, 30, 30)), (0.8 * W, 0.2 * H)))
        sc["_p"] = dict(items=items, shapes=shapes)

    def draw(self, t, sc, last):
        W, H, S, P = self.W, self.H, self.S, sc["_p"]
        lt = t - sc["start"]
        cv = self.bg.copy()
        k = ease_out_back(lt / 0.5)
        for n, (spr, (cx, cy)) in enumerate(P["shapes"]):
            paste_center(cv, spr, cx, cy + math.sin(t * 0.9 + n) * 12 * S, 0.2 + 0.8 * k, min(lt / 0.2, 1))
        d = ImageDraw.Draw(cv)
        w3 = max(2, int(3 * S))
        x0, y0, L = 0.80 * W, 0.075 * H, 0.12 * W
        d.line([(x0, y0), (x0 + L, y0), (x0 + L, y0 + L)], fill=(40, 40, 40), width=w3)
        for j in range(5):
            y = 0.07 * H + j * 15 * S
            d.line([(0.07 * W, y), (0.07 * W + (0.22 - 0.025 * j) * W, y)], fill=(120, 120, 120), width=max(1, int(2 * S)))
        self.words(sc, t, last, cv)
        sig = self.o.get("signature")
        if last and sig and lt > 0.8:
            f = get_font("PinyonScript-Regular.ttf", sig, 90 * S)
            txt = "edit by  " + sig
            d.text((W / 2, 0.62 * H), txt, font=f, fill=(40, 40, 40), anchor="mm")
        return cv


# ───────────────────────── 2) سينمائي تركوازي ─────────────────────────
class Cinematic(Style):
    key = "cinematic_teal"
    max_words = 3
    GLOWS = [(255, 106, 26), (26, 174, 159), (70, 120, 255)]

    def __init__(self, W, H, o):
        super().__init__(W, H, o)
        self.teal = self.pal["accent"]
        self.light = gradient(W, H, (255, 255, 255), (214, 243, 240), "v")
        self.darks = {}

    def _dark(self, gi):
        if gi not in self.darks:
            g = self.GLOWS[gi]
            self.darks[gi] = radial(self.W, self.H, 0.5 * self.W, 0.58 * self.H, 0.95 * self.H,
                                    tuple(int(c * 0.5) for c in g), (0, 0, 0))
        return self.darks[gi]

    def prepare(self, sc):
        W, H, S, i = self.W, self.H, self.S, sc["idx"]
        dark = i % 2 == 1
        gi = (i // 2) % 3
        base = dict(latin="ArchivoBlack-Regular.ttf", arabic="Tajawal-Black.ttf", base=120, emph_scale=1.12,
                    cy=0.5, max_w=0.8, max_lines=3, line_gap=1.05, upper=False)
        if dark:
            g = self.GLOWS[gi]
            light_g = tuple(min(255, int(c * 0.4 + 150)) for c in g)
            cfg = dict(base, color=(255, 255, 255), emph_color=light_g, emph_box=None, emph_text=None,
                       shadow=(g, 10, (0, 0)))
        else:
            cfg = dict(base, color=(255, 255, 255), emph_color=(8, 60, 56), emph_box=(255, 255, 255),
                       emph_text=(8, 90, 82), shadow=((0, 70, 64), 6, (0, 6)))
        items, _ = build_words(sc, W, H, cfg)
        P = dict(items=items, dark=dark, gi=gi)
        if dark:
            rng = random.Random(i)
            P["parts"] = [(rng.random() * W, rng.random() * H, 40 + rng.random() * 120, rng.randint(3, 9) * S,
                           rng.random() * 6.28) for _ in range(46)]
            P["dots"] = {}
        else:
            P["circle"] = circle(int(0.82 * W), self.teal)
        sc["_p"] = P

    def draw(self, t, sc, last):
        W, H, S, P = self.W, self.H, self.S, sc["_p"]
        lt = t - sc["start"]
        if P["dark"]:
            cv = self._dark(P["gi"]).copy()
            col = self.GLOWS[P["gi"]]
            for x, y0, sp, sz, ph in P["parts"]:
                y = (y0 - sp * S * t) % (H + 80) - 40
                xx = x + math.sin(t * 0.8 + ph) * 25 * S
                key = int(sz)
                if key not in P["dots"]:
                    P["dots"][key] = dot(key, col)
                paste_center(cv, P["dots"][key], xx, y, 1, 0.55 + 0.45 * math.sin(t * 3 + ph))
        else:
            cv = self.light.copy()
            paste_center(cv, P["circle"], 0.5 * W, 0.5 * H, 0.3 + 0.7 * ease_out_back(lt / 0.55), min(lt / 0.2, 1))
        if lt < 0.18:
            cv = Image.blend(Image.new("RGB", cv.size, (255, 255, 255) if not P["dark"] else (0, 0, 0)), cv, lt / 0.18)
        self.words(sc, t, last, cv)
        return cv


# ───────────────────────── 3) تقني رمادي ─────────────────────────
class Tech(Style):
    key = "ai_tech_gray"
    max_words = 5
    anim = "rise"

    def __init__(self, W, H, o):
        super().__init__(W, H, o)
        self.bg = Image.new("RGB", (W, H), (237, 237, 237))

    def prepare(self, sc):
        W, H, S, i = self.W, self.H, self.S, sc["idx"]
        cfg = dict(latin="ArchivoBlack-Regular.ttf", arabic="Tajawal-Black.ttf", base=92, emph_scale=1.3,
                   color=(30, 30, 30), emph_color=(255, 255, 255), emph_box=(17, 17, 17), emph_text=(255, 255, 255),
                   shadow=None, cy=0.5, max_w=0.72, max_lines=4, line_gap=1.12, upper=False)
        items, bb = build_words(sc, W, H, cfg)
        pad = 0.07 * W
        cw, ch = min(bb[2] - bb[0] + 2 * pad, 0.94 * W), bb[3] - bb[1] + 2 * pad
        a = AA(int(cw), int(ch))
        a.rrect((0, 0, a.w - 1, a.h - 1), 0.05 * W, fill=(255, 255, 255, 255))
        card = with_shadow(a.done(), blur=30 * S, offset=(0, 18 * S), alpha=70)
        rng = random.Random(i * 7 + 3)
        circles = []
        for d, g in ((0.95, 218), (0.55, 208), (0.34, 224)):
            circles.append((circle(int(d * W), (g, g, g), shadow=False),
                            (rng.uniform(0.05, 0.95) * W, rng.uniform(0.08, 0.92) * H), rng.uniform(0, 6)))
        sc["_p"] = dict(items=items, card=card, ccx=(bb[0] + bb[2]) / 2, ccy=(bb[1] + bb[3]) / 2, circles=circles)

    def draw(self, t, sc, last):
        S, P = self.S, sc["_p"]
        lt = t - sc["start"]
        cv = self.bg.copy()
        for spr, (cx, cy), ph in P["circles"]:
            paste_center(cv, spr, cx + math.sin(t * 0.6 + ph) * 30 * S, cy + math.cos(t * 0.5 + ph) * 25 * S)
        k = ease_out_cubic(lt / 0.45)
        dy = (1 - k) * 0.12 * self.H
        paste_center(cv, P["card"], P["ccx"], P["ccy"] + dy, 1, k)
        self.words(sc, t, last, cv, dy=dy, alpha_mul=k)
        return cv


# ───────────────────────── 4) ترجمة متحركة ─────────────────────────
class Captions(Style):
    key = "captions_pop"
    max_words = 4

    def __init__(self, W, H, o):
        super().__init__(W, H, o)
        self.red = self.pal["accent"]
        self.dark = gradient(W, H, (10, 10, 10), (52, 52, 56), "d")
        p = self.o.get("bg_image")
        if p:
            try:
                im = Image.open(p).convert("RGB")
                r = max(W / im.width, H / im.height)
                im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
                l, tp = (im.width - W) // 2, (im.height - H) // 2
                self.dark = Image.blend(im.crop((l, tp, l + W, tp + H)), Image.new("RGB", (W, H), (0, 0, 0)), 0.55)
            except Exception:
                pass
        self.light = gradient(W, H, (252, 252, 252), (204, 204, 210), "d")

    def prepare(self, sc):
        W, H, i = self.W, self.H, sc["idx"]
        flash = i % 4 == 3
        cfg = dict(latin="ArchivoBlack-Regular.ttf", arabic="Tajawal-Black.ttf", base=112, emph_scale=1.0,
                   color=(17, 17, 17) if flash else (255, 255, 255), emph_color=(255, 255, 255),
                   emph_box=self.red, emph_text=(255, 255, 255), shadow=((0, 0, 0), 7, (0, 8)),
                   cy=0.5 if flash else 0.64, max_w=0.86, max_lines=3, line_gap=1.1, upper=False)
        items, _ = build_words(sc, W, H, cfg)
        sc["_p"] = dict(items=items, flash=flash)

    def draw(self, t, sc, last):
        P = sc["_p"]
        lt = t - sc["start"]
        cv = (self.light if P["flash"] else self.dark).copy()
        if P["flash"] and lt < 0.12:
            cv = Image.blend(Image.new("RGB", cv.size, (255, 255, 255)), cv, lt / 0.12)
        self.words(sc, t, last, cv)
        return cv


# ───────────────────────── 5) شرح عربي ─────────────────────────
class Explainer(Style):
    key = "arabic_explainer"
    max_words = 6

    def __init__(self, W, H, o):
        super().__init__(W, H, o)
        self.bg = Image.new("RGB", (W, H), (247, 241, 227))
        self.pres = None
        p = self.o.get("presenter")
        if p:
            try:
                im = Image.open(p).convert("RGBA")
                r = 0.36 * H / im.height
                self.pres = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
            except Exception:
                pass

    def _illus(self, kind):
        W, S = self.W, self.S
        dk, gr, rd = (31, 58, 54, 255), (47, 125, 98, 255), (215, 20, 26, 255)
        if kind == 0:  # هاتف
            w, h = int(0.30 * W), int(0.52 * W)
            a = AA(w, h)
            a.rrect((0, 0, w - 1, h - 1), w * 0.12, fill=dk)
            a.rrect((w * .07, h * .05, w * .93, h * .95), w * 0.08, fill=(232, 241, 236, 255))
            a.rrect((w * .15, h * .1, w * .6, h * .15), 6, fill=gr)
            for j in range(3):
                a.rrect((w * .15, h * (.22 + j * .17), w * .85, h * (.34 + j * .17)), 8, fill=(255, 255, 255, 255), outline=dk, width=2)
            a.rrect((w * .2, h * .82, w * .8, h * .9), 10, fill=rd)
        elif kind == 1:  # قائمة تحقق
            w, h = int(0.56 * W), int(0.42 * W)
            a = AA(w, h)
            for j in range(3):
                y = j * h / 3
                a.rrect((0, y + 4, w - 1, y + h / 3 - 8), 18, fill=(255, 255, 255, 255), outline=dk, width=3)
                r = h / 3 - 28
                a.ellipse((14, y + 14, 14 + r, y + 14 + r), fill=gr)
                a.line([(14 + r * .25, y + 14 + r * .52), (14 + r * .43, y + 14 + r * .7), (14 + r * .78, y + 14 + r * .3)], (255, 255, 255, 255), 5)
                a.rrect((r + 40, y + h / 6 - 8, w - 30, y + h / 6 + 8), 8, fill=(200, 200, 200, 255))
        elif kind == 2:  # مجلد
            w, h = int(0.5 * W), int(0.36 * W)
            a = AA(w, h)
            a.rrect((0, 0, w * .4, h * .2), 12, fill=(36, 98, 76, 255))
            a.rrect((0, h * .1, w - 1, h - 1), 20, fill=gr)
            a.rrect((w * .2, h * .42, w * .8, h * .68), 10, fill=(255, 255, 255, 255))
        else:  # إحصائيات
            w, h = int(0.5 * W), int(0.38 * W)
            a = AA(w, h)
            for j, (bh, c) in enumerate(((.45, gr), (.75, rd), (.6, dk))):
                a.rrect((w * (.08 + j * .22), h * (1 - bh), w * (.24 + j * .22), h - 1), 10, fill=c)
            a.arc((w * .72, h * .05, w * .98, h * .05 + w * .26), 130, 400, rd, 12)
        return with_shadow(a.done(), blur=10 * S, offset=(6 * S, 8 * S), alpha=50)

    def prepare(self, sc):
        W, H, S, i = self.W, self.H, self.S, sc["idx"]
        cfg = dict(latin="ArchivoBlack-Regular.ttf", arabic="Tajawal-Black.ttf", base=82, emph_scale=1.0,
                   color=(26, 26, 26), emph_color=(215, 20, 26), emph_box=None, emph_text=None, shadow=None,
                   cy=0.32, max_w=0.68, max_lines=4, line_gap=1.12, upper=False)
        items, bb = build_words(sc, W, H, cfg)
        pad = 0.05 * W
        bw, bh = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
        a = AA(int(bw + 16), int(bh + 16))
        a.rrect((14, 14, a.w - 1, a.h - 1), 0.04 * W, fill=(26, 26, 26, 255))
        a.rrect((0, 0, a.w - 15, a.h - 15), 0.04 * W, fill=(255, 255, 255, 255), outline=(26, 26, 26, 255), width=max(4, 6 * S))
        sc["_p"] = dict(items=items, bubble=a.done(), bcx=(bb[0] + bb[2]) / 2 + 7, bcy=(bb[1] + bb[3]) / 2 + 7,
                        illus=self._illus(i % 4), q=(i % 2 == 0), bbox=bb, pad=pad)

    def draw(self, t, sc, last):
        W, H, S, P = self.W, self.H, self.S, sc["_p"]
        lt = t - sc["start"]
        cv = self.bg.copy()
        paste_center(cv, P["bubble"], P["bcx"], P["bcy"], 0.7 + 0.3 * ease_out_back(lt / 0.4), min(lt / 0.15, 1))
        if P["q"] and lt > 0.2:
            d = int(0.11 * W)
            a = AA(d, d)
            a.ellipse((0, 0, d - 1, d - 1), fill=(215, 20, 26, 255))
            qf = get_font("ArchivoBlack-Regular.ttf", "?", d * 0.7)
            q = a.done()
            ImageDraw.Draw(q).text((d / 2, d / 2), "?", font=qf, fill=(255, 255, 255, 255), anchor="mm")
            bb = P["bbox"]
            paste_center(cv, q, bb[0] - P["pad"] * 0.2, bb[1] - P["pad"] * 0.6, 0.5 + 0.5 * ease_out_back((lt - 0.2) / 0.35), 1)
        ix = 0.64 * W if self.pres else 0.5 * W
        paste_center(cv, P["illus"], ix, 0.74 * H, 0.75 + 0.25 * ease_out_back((lt - 0.15) / 0.5), min(max(lt - 0.15, 0) / 0.2, 1))
        if self.pres:
            cv.paste(self.pres, (int(0.01 * W), int(H - self.pres.height + math.sin(t * 2) * 6 * S)), self.pres)
        self.words(sc, t, last, cv)
        return cv


STYLES = {c.key: c for c in (Editorial, Cinematic, Tech, Captions, Explainer)}
