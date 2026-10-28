"""جسر التوافق: قص الصمت (auto_cut) + التفريغ بالدارجة (transcriber) بصيغة تفهمها المنصة.

ملاحظات إصلاح مهمة على سلوك الملفين الأصليين:
- قص الصوت هنا يتم بـ ffmpeg (atrim + concat) بدقة كاملة وبدون حدّ 48 مقطعاً؛
  الحد الأصلي في _build_ffmpeg_select_expr كان يدمج المقاطع القريبة فيعيد الصمت ويفسد تزامن الكلمات.
- إذا فشلت معايرة auto_cut (تُبقي الملف كاملاً عندما يكون الكلام أقل من 45%) نستعمل كاشفاً احتياطياً.
- التفريغ يتم على الصوت بعد القص، فتكون توقيتات الكلمات مطابقة للصوت النهائي تماماً.
"""
import os
import subprocess
import wave

import numpy as np

from . import auto_cut, transcriber


def _run(cmd, err):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(err + " " + r.stderr.decode(errors="ignore")[-200:])


def _dbfs(wav_path, step_ms=20):
    with wave.open(wav_path, "rb") as wf:
        sr, raw = wf.getframerate(), wf.readframes(wf.getnframes())
    x = np.frombuffer(raw, np.int16).astype(np.float32)
    w = max(1, int(sr * step_ms / 1000))
    n = len(x) // w
    if n < 2:
        return np.array([-90.0]), step_ms
    r = np.sqrt(np.mean(x[: n * w].reshape(n, w) ** 2, axis=1) + 1e-9)
    return 20 * np.log10(np.maximum(r / 32768.0, 1e-7)), step_ms


def _to_wav(src, dst, sr, ch=1):
    _run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", str(ch), "-ar", str(sr),
          "-acodec", "pcm_s16le", dst], "فشل قراءة الصوت.")


def _threshold(db):
    v = db[db > -85]
    if len(v) < 5:
        return -45.0
    return max(float(np.percentile(v, 10)) + 9.0, float(np.percentile(v, 90)) - 26.0)


def _own_intervals(db, step_ms, min_sil=0.25, pad=0.08):
    """كاشف احتياطي: عتبة نسبية من مستوى الكلام والضجيج، يقص كل صمت ≥ 250ms ويُبقي نفَساً طبيعياً."""
    st = step_ms / 1000.0
    sp = db >= _threshold(db)
    runs, i = [], 0
    while i < len(sp):
        if sp[i]:
            j = i
            while j < len(sp) and sp[j]:
                j += 1
            if (j - i) * st >= 0.06:
                runs.append([i * st, j * st])
            i = j
        else:
            i += 1
    if not runs:
        return []
    merged = [runs[0]]
    for s, e in runs[1:]:
        if s - merged[-1][1] < min_sil:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    total = len(db) * st
    return [(max(0.0, s - pad), min(total, e + pad)) for s, e in merged]


def _sanitize(ints, dur):
    out = []
    for s, e in sorted((max(0.0, a), min(dur, b)) for a, b in ints):
        if e - s < 0.08:
            continue
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def _cut(src, ints, dst):
    """قص دقيق بدون حد للمقاطع (filter_complex_script)."""
    fd = 0.004
    parts, labels = [], ""
    for i, (s, e) in enumerate(ints):
        d = e - s
        parts.append(f"[0:a]atrim=start={s:.4f}:end={e:.4f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d={fd},afade=t=out:st={max(d - fd, 0):.4f}:d={fd}[a{i}]")
        labels += f"[a{i}]"
    parts.append(f"{labels}concat=n={len(ints)}:v=0:a=1[out]")
    script = dst + ".filter.txt"
    open(script, "w").write(";\n".join(parts))
    _run(["ffmpeg", "-y", "-v", "error", "-i", src, "-filter_complex_script", script, "-map", "[out]",
          "-ar", "44100", "-ac", "1", "-acodec", "pcm_s16le", dst], "فشل قص الصمت.")
    os.remove(script)


def clean_audio(src, workdir, cut_silence=True):
    """يعيد (مسار wav نظيف، إحصاءات)."""
    os.makedirs(workdir, exist_ok=True)
    out = os.path.join(workdir, "clean.wav")
    dur = transcriber_duration(src)
    if not cut_silence:
        _to_wav(src, out, 44100)
        return out, dict(orig=dur, new=dur, removed_pct=0.0, residual_pct=None, segments=1, method="none")
    w16 = os.path.join(workdir, "scan16k.wav")
    _to_wav(src, w16, 16000)
    db, step = _dbfs(w16)
    th = _threshold(db)
    method, ints = "auto_cut", None
    try:
        ints, _ = auto_cut.detect_speech_intervals_fast(src, workdir)
    except Exception:
        ints = None
    ints = _sanitize(ints or [], dur)
    kept = sum(e - s for s, e in ints)
    if not ints or kept > 0.9 * dur:  # لم يقصّ شيئاً تقريباً: جرّب الكاشف الاحتياطي
        alt = _sanitize(_own_intervals(db, step), dur)
        if alt and sum(e - s for s, e in alt) < kept or not ints:
            ints, method = alt, "fallback"
    if not ints or sum(e - s for s, e in ints) < 1.0:
        _to_wav(src, out, 44100)
        return out, dict(orig=dur, new=dur, removed_pct=0.0, residual_pct=None, segments=1, method="none")
    _cut(src, ints, out)
    db2, _ = _dbfs_from(out)
    new = len(db2) * step / 1000.0
    resid = float(np.mean(db2 < th) * 100)
    os.remove(w16) if os.path.exists(w16) else None
    return out, dict(orig=dur, new=new, removed_pct=round((1 - new / dur) * 100, 1),
                     residual_pct=round(resid, 1), segments=len(ints), method=method)


def _dbfs_from(wav44):
    w = wav44 + ".16k.wav"
    _to_wav(wav44, w, 16000)
    r = _dbfs(w)
    os.remove(w)
    return r


def transcriber_duration(path):
    from .stt import audio_duration
    return audio_duration(path)


def transcribe(clean_wav, lang="ar_dz", groq_key="", gemini_key=""):
    """تفريغ عبر transcriber.py بدون مفاتيح: Google ar-DZ (دارجة جزائرية) ثم Whisper المحلي.
    lang: ar_dz (دارجة جزائرية) | ar (فصحى/لهجات أخرى) | en | auto. المفاتيح اختيارية تماماً."""
    code = "ar" if lang.startswith("ar") else lang
    dm = "algerian_darija" if lang == "ar_dz" else "standard"
    words = transcriber.transcribe_audio(clean_wav, model_size="small", language=code, dialect_mode=dm,
                                         groq_api_key=groq_key or None, gemini_api_key=gemini_key or None)
    dur = transcriber_duration(clean_wav)
    out, last = [], 0.0
    for w in words or []:
        t = str(w.get("word", "")).strip()
        if not t:
            continue
        s = min(max(float(w["start"]), last), dur)
        e = min(max(float(w["end"]), s + 0.05), dur)
        out.append(dict(text=t, s=s, e=e))
        last = s
    return out
