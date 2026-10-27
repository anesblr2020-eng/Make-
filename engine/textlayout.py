"""تخطيط الكلمات: كل كلمة صورة (sprite) تظهر في لحظة نطقها."""
from PIL import Image, ImageDraw, ImageFilter
from .fonts import get_font
from .textutil import has_ar, shape
from .shapes import ease_out_back, ease_out_cubic, paste_center


def make_sprite(text, font, color, box=None, box_text=None, shadow=None):
    shaped = shape(text)
    asc, desc = font.getmetrics()
    tw = int(font.getlength(shaped))
    pad = int(max(font.size * 0.4, 12))
    img = Image.new("RGBA", (tw + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    if box:
        bx, by = int(font.size * 0.18), int(font.size * 0.04)
        ImageDraw.Draw(img).rounded_rectangle(
            (pad - bx, pad + asc * 0.08 - by, pad + tw + bx, pad + asc + desc * 0.55 + by),
            radius=int(font.size * 0.1), fill=tuple(box) + (255,))
        color = box_text or color
    if shadow:
        scol, blur, off = shadow
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad + off[0], pad + off[1]), shaped, font=font, fill=tuple(scol) + (230,))
        sh = sh.filter(ImageFilter.GaussianBlur(blur))
        img.alpha_composite(sh)
    ImageDraw.Draw(img).text((pad, pad), shaped, font=font, fill=tuple(color) + (255,))
    return img, pad


def build_words(sc, W, H, cfg):
    S = W / 1080
    words = sc["words"]
    texts = [w["text"].upper() if cfg.get("upper") and not has_ar(w["text"]) else w["text"] for w in words]
    size, minsize, maxw = cfg["base"] * S, cfg["base"] * S * 0.4, cfg["max_w"] * W
    while True:
        meas = []
        for w, tx in zip(words, texts):
            sz = size * (cfg["emph_scale"] if w["emph"] else 1)
            f = get_font(cfg["latin"], tx, sz, cfg["arabic"])
            meas.append((f, int(f.getlength(shape(tx)))))
        space = 0.26 * size
        lines, cur, cw = [], [], 0
        for i, (_, tw) in enumerate(meas):
            add = tw if not cur else space + tw
            if cur and cw + add > maxw:
                lines.append(cur)
                cur, cw = [i], tw
            else:
                cur.append(i)
                cw += add
        if cur:
            lines.append(cur)
        widest = max(sum(meas[i][1] for i in l) + space * (len(l) - 1) for l in lines)
        if (len(lines) <= cfg["max_lines"] and widest <= maxw * 1.02) or size <= minsize:
            break
        size *= 0.9
    ad = [m[0].getmetrics() for m in meas]
    info = [(max(ad[i][0] for i in l), max(ad[i][1] for i in l)) for l in lines]
    heights = [(a + d) * cfg["line_gap"] for a, d in info]
    y = cfg["cy"] * H - sum(heights) / 2
    rtl = any(has_ar(t) for t in texts)
    items = []
    for l, (la, _), hh in zip(lines, info, heights):
        lw = sum(meas[i][1] for i in l) + space * (len(l) - 1)
        x = (W + lw) / 2 if rtl else (W - lw) / 2
        for i in l:
            f, tw = meas[i]
            w = words[i]
            emph = w["emph"]
            box = cfg.get("emph_box") if emph else None
            col = cfg["emph_color"] if emph else cfg["color"]
            spr, pad = make_sprite(texts[i], f, col, box, cfg.get("emph_text"), cfg.get("shadow"))
            tx = x - tw if rtl else x
            ty = y + la - ad[i][0]
            items.append(dict(spr=spr, x=tx - pad, y=ty - pad, w=spr.width, h=spr.height,
                              s=max(w["s"], sc["start"]), tx=tx, ty=ty, tw=tw, th=ad[i][0] + ad[i][1]))
            x = x - (tw + space) if rtl else x + tw + space
        y += hh
    bbox = (min(i["tx"] for i in items), min(i["ty"] for i in items),
            max(i["tx"] + i["tw"] for i in items), max(i["ty"] + i["th"] for i in items))
    return items, bbox


def draw_words(cv, items, t, text_end, last, anim, S, dy=0.0, alpha_mul=1.0):
    fade = 0.12
    for it in items:
        a = t - it["s"]
        if a < 0 or t > text_end:
            continue
        p = min(a / 0.28, 1.0)
        al = min(a / 0.12, 1.0) * alpha_mul
        if not last and text_end - t < fade:
            al *= max((text_end - t) / fade, 0)
        cx, cy = it["x"] + it["w"] / 2, it["y"] + it["h"] / 2 + dy
        sc = 1.0
        if anim == "pop":
            sc = 0.6 + 0.4 * ease_out_back(p)
        elif anim == "rise":
            cy += (1 - ease_out_cubic(p)) * 50 * S
        paste_center(cv, it["spr"], cx, cy, sc, al)
