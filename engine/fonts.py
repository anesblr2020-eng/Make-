"""تحميل الخطوط: من مجلد fonts/ ثم تنزيل تلقائي من Google Fonts ثم خط النظام."""
import os
import urllib.request
from functools import lru_cache
from pathlib import Path
from PIL import ImageFont
from .textutil import has_ar, USE_RESHAPER

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "fonts"
B = "https://github.com/google/fonts/raw/main/ofl/"
SOURCES = {
    "Anton-Regular.ttf": B + "anton/Anton-Regular.ttf",
    "ArchivoBlack-Regular.ttf": B + "archivoblack/ArchivoBlack-Regular.ttf",
    "PinyonScript-Regular.ttf": B + "pinyonscript/PinyonScript-Regular.ttf",
    "Tajawal-Black.ttf": B + "tajawal/Tajawal-Black.ttf",
    "Tajawal-Bold.ttf": B + "tajawal/Tajawal-Bold.ttf",
}
FALLBACKS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]
_failed = set()


def _path(name):
    p = FONT_DIR / name
    if p.exists() and p.stat().st_size > 1000:
        return str(p)
    if name in SOURCES and name not in _failed:
        try:
            FONT_DIR.mkdir(exist_ok=True)
            req = urllib.request.Request(SOURCES[name], headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=10).read()
            if len(data) > 1000:
                p.write_bytes(data)
                return str(p)
        except Exception:
            pass
        _failed.add(name)
    for f in FALLBACKS:
        if os.path.exists(f):
            return f
    return None


@lru_cache(maxsize=256)
def _load(path, size):
    kw = {"layout_engine": ImageFont.Layout.BASIC} if USE_RESHAPER else {}
    try:
        return ImageFont.truetype(path, size, **kw)
    except Exception:
        return ImageFont.load_default(size)


def get_font(latin, text, size, arabic="Tajawal-Black.ttf"):
    name = arabic if has_ar(text) else latin
    p = _path(name)
    return _load(p, max(8, int(size))) if p else ImageFont.load_default(max(8, int(size)))
