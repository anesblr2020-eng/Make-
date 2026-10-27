"""المخطط: يحوّل الكلمات المؤقّتة إلى مشاهد بقواعد بسيطة (بدون أي ذكاء اصطناعي مدفوع)."""
import re

STOP = set("""a an the and or but of to in on at for with is are was were be been it this that these those i you he she we
they my your our their as by from so if then than just not no yes do does did have has had من في على الى إلى عن مع هذا
هذه ذلك تلك هو هي هم هن انا أنا انت أنت نحن ما لا لم لن إن ان أن كان كانت التي الذي الذين و او أو ثم قد كل بعد قبل عند
حتى لكن بل""".split())
END_PUNCT = re.compile(r"[.!?؟،,;:…]$")


def _clean(w):
    return re.sub(r"[^\w\u0600-\u06FF]", "", w)


def _display(w):
    return w.strip().rstrip('.,;:،؛…"“”')


def _pick_emph(ws):
    idx = [i for i, w in enumerate(ws) if any(c.isdigit() for c in w["text"])]
    if not idx:
        idx = [i for i, w in enumerate(ws) if _clean(w["text"]).lower() not in STOP and len(_clean(w["text"])) >= 3]
    if not idx:
        idx = list(range(len(ws)))
    return max(idx, key=lambda i: len(_clean(ws[i]["text"])))


def make_scenes(words, total, max_words=4, gap=0.45):
    words = [dict(text=_display(w["text"]), s=float(w["s"]), e=float(w["e"]), raw=w["text"])
             for w in words if _clean(w["text"])]
    phrases, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["s"] - cur[-1]["e"] > gap):
            phrases.append(cur)
            cur = []
        cur.append(w)
        if END_PUNCT.search(w["raw"].strip()) and len(cur) >= 2:
            phrases.append(cur)
            cur = []
    if cur:
        phrases.append(cur)
    scenes = []
    for i, ph in enumerate(phrases):
        e = _pick_emph(ph)
        ws = [dict(text=w["text"], s=w["s"], e=w["e"], emph=(j == e)) for j, w in enumerate(ph)]
        start = 0.0 if i == 0 else max(ph[0]["s"] - 0.05, scenes[-1]["start"] + 0.2)
        scenes.append(dict(idx=i, start=start, words=ws))
    for i, sc in enumerate(scenes):
        sc["end"] = scenes[i + 1]["start"] if i + 1 < len(scenes) else total + 1
        sc["text_end"] = min(sc["end"], sc["words"][-1]["e"] + 0.9) if i + 1 < len(scenes) else total + 1
    return scenes
