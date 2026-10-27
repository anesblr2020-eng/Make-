"""الرسم على مراحل: كل ~15 ثانية في ملف مستقل، ثم دمج الأجزاء مع الصوت."""
import math
import subprocess
import time
from pathlib import Path
from .planner import make_scenes
from .stt import audio_duration
from .styles import STYLES


def _ffmpeg_chunk(W, H, fps, out, log):
    return subprocess.Popen(
        ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", str(out)],
        stdin=subprocess.PIPE, stderr=open(log, "wb"))


def render(audio, words, style_key, opts, out_path, workdir, size=(1080, 1920), fps=30, chunk_sec=15, progress=None):
    W, H = size
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    dur = audio_duration(audio)
    style = STYLES[style_key](W, H, opts)
    scenes = make_scenes(words, dur, style.max_words)
    if not scenes:
        raise RuntimeError("لا توجد كلمات لعرضها.")
    total = int(math.ceil(dur * fps))
    cf = int(chunk_sec * fps)
    nchunks = math.ceil(total / cf)
    si, done, t0 = 0, 0, time.time()
    style.prepare(scenes[0])
    chunks = []
    for k in range(nchunks):
        f0, f1 = k * cf, min((k + 1) * cf, total)
        out = workdir / f"c{k:03d}.mp4"
        chunks.append(out)
        if out.exists() and out.stat().st_size > 1000:  # استئناف: المرحلة منجزة سابقاً
            done = f1
            continue
        part, log = workdir / f"c{k:03d}.part.mp4", workdir / f"c{k:03d}.log"
        p = _ffmpeg_chunk(W, H, fps, part, log)
        try:
            for f in range(f0, f1):
                t = f / fps
                while si + 1 < len(scenes) and t >= scenes[si + 1]["start"]:
                    style.release(scenes[si])
                    si += 1
                    if "_p" not in scenes[si]:
                        style.prepare(scenes[si])
                if "_p" not in scenes[si]:
                    style.prepare(scenes[si])
                p.stdin.write(style.draw(t, scenes[si], si == len(scenes) - 1).tobytes())
                done += 1
                if progress and f % 15 == 0:
                    el = time.time() - t0
                    eta = el / max(done, 1) * (total - done)
                    progress(done / total * 0.95, f"المرحلة {k + 1} من {nchunks} — متبقٍّ تقريباً {int(eta)} ث")
            p.stdin.close()
            if p.wait() != 0:
                raise RuntimeError("فشل الترميز: " + Path(log).read_text(errors="ignore")[-300:])
        except BrokenPipeError:
            raise RuntimeError("توقف ffmpeg: " + Path(log).read_text(errors="ignore")[-300:])
        part.rename(out)
    lst = workdir / "list.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in chunks))
    if progress:
        progress(0.97, "دمج المراحل مع الصوت…")
    r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(audio),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        "-movflags", "+faststart", str(out_path)], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("فشل الدمج: " + r.stderr.decode(errors="ignore")[-300:])
    if progress:
        progress(1.0, "اكتمل")
    return out_path
