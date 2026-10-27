"""تحويل الصوت إلى كلمات مؤقّتة: Groq Whisper (مجاني) أو نص يدوي بتوزيع زمني تلقائي."""
import re
import subprocess
import requests

URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def audio_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        raise RuntimeError("تعذّر قراءة ملف الصوت. جرّب mp3 أو wav أو m4a.")


def _to_mp3(src, dst):
    r = subprocess.run(["ffmpeg", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", dst],
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("فشل تحويل الصوت. تأكد أن الملف سليم.")


def transcribe_groq(path, key, lang=None, workdir="/tmp"):
    mp3 = f"{workdir}/stt.mp3"
    _to_mp3(path, mp3)
    data = {"model": "whisper-large-v3-turbo", "response_format": "verbose_json",
            "timestamp_granularities[]": ["word", "segment"], "temperature": "0"}
    if lang:
        data["language"] = lang
    with open(mp3, "rb") as f:
        r = requests.post(URL, headers={"Authorization": f"Bearer {key.strip()}"},
                          files={"file": ("a.mp3", f, "audio/mpeg")}, data=data, timeout=180)
    if r.status_code == 401:
        raise RuntimeError("مفتاح Groq غير صحيح.")
    if r.status_code == 429:
        raise RuntimeError("تجاوزت حدّ الاستخدام المجاني في Groq. انتظر قليلاً أو استخدم النص اليدوي.")
    if r.status_code != 200:
        raise RuntimeError(f"خطأ من Groq ({r.status_code}): {r.text[:160]}")
    j = r.json()
    words = [dict(text=w["word"].strip(), s=w["start"], e=w["end"]) for w in j.get("words") or [] if w["word"].strip()]
    if not words:  # لا توجد توقيتات كلمات: نوزّع كل مقطع على كلماته
        for seg in j.get("segments") or []:
            words += words_from_text(seg["text"], seg["end"] - seg["start"], 0, 0, offset=seg["start"])
    if not words:
        raise RuntimeError("لم يُكتشف كلام في الملف.")
    return words, j.get("text", "")


def words_from_text(text, dur, lead=0.2, tail=0.3, offset=0.0):
    toks = text.split()
    if not toks:
        return []
    wt = [len(re.sub(r"\W", "", t)) + 1 + (3 if re.search(r"[.!?؟،,;:]$", t) else 0) for t in toks]
    unit = max(dur - lead - tail, 0.5) / sum(wt)
    out, t = [], offset + lead
    for tok, w in zip(toks, wt):
        out.append(dict(text=tok, s=t, e=t + unit * (w - (3 if w > len(tok) + 1 else 0)) * 0.95))
        t += unit * w
    return out
