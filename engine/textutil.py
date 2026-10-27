"""أدوات النص العربي: التشكيل واتجاه الكتابة."""
try:
    import arabic_reshaper
    try:
        from bidi import get_display
    except Exception:
        from bidi.algorithm import get_display
    USE_RESHAPER = True
except Exception:
    USE_RESHAPER = False


def has_ar(s):
    return any("\u0600" <= c <= "\u06ff" or "\u0750" <= c <= "\u077f" for c in s)


def shape(s):
    if USE_RESHAPER and has_ar(s):
        return get_display(arabic_reshaper.reshape(s))
    return s
