import json
import shutil
import tempfile
import time
from pathlib import Path

import streamlit as st

from engine.renderer import render
from engine.stt import audio_duration, transcribe_groq, words_from_text
from engine.styles import PRESETS

st.set_page_config(page_title="MotionAI | منصة الموشن جرافيك", page_icon="🎬", layout="centered")
st.markdown("""<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {direction: rtl; text-align: right;}
.stTextInput input, .stTextArea textarea {direction: rtl; text-align: right;}
[data-testid="stFileUploader"] section {direction: rtl;}
</style>""", unsafe_allow_html=True)

st.title("🎬 MotionAI — منصة الموشن جرافيك")
st.caption("ارفع تسجيلاً صوتياً، واختر الستايل، وستحصل على فيديو موشن جرافيك طولي جاهز للتيك توك والريلز. مجاني بالكامل.")

labels = {k: v["label"] for k, v in PRESETS.items()}
audio = st.file_uploader("① ارفع الملف الصوتي (mp3 / wav / m4a / ogg)", type=["mp3", "wav", "m4a", "ogg", "aac", "mp4"])
style = st.selectbox("② اختر الستايل", list(labels), format_func=lambda k: labels[k])

with st.expander("③ إعدادات التفريغ الصوتي (مجاني)", expanded=True):
    try:
        secret_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        secret_key = ""
    key = st.text_input("مفتاح Groq المجاني (بدون بطاقة)", value=secret_key, type="password",
                        help="أنشئه مجاناً من console.groq.com ← API Keys")
    lang = st.selectbox("لغة الكلام", ["تلقائي", "العربية", "English"])
    manual = st.text_area("أو الصق نص الكلام هنا (بديل بدون مفتاح؛ يوزَّع زمنه تلقائياً على الصوت)", height=100)

with st.expander("④ خيارات إضافية (اختيارية)"):
    quality = st.radio("الجودة", ["1080p (1080×1920) — الأفضل", "720p (720×1280) — أسرع"], index=0)
    fps = st.radio("الإطارات في الثانية", [30, 24], horizontal=True)
    signature = st.text_input("اسمك للتوقيع الختامي (ستايل التحريري فقط)")
    bg_img = st.file_uploader("صورة خلفية (ستايل الترجمة المتحركة فقط)", type=["png", "jpg", "jpeg"])
    pres_img = st.file_uploader("صورة شخصية PNG شفافة (ستايل الشرح العربي فقط)", type=["png"])

st.info("⏱️ الاستضافة المجانية بطيئة نسبياً: دقيقة صوت بجودة 1080p قد تستغرق عدة دقائق. يُرسم الفيديو على مراحل "
        "(كل ~15 ثانية)، ولا تغلق الصفحة أثناء العمل.")

if st.button("🚀 أنشئ الفيديو", type="primary", disabled=audio is None):
    work = Path(tempfile.mkdtemp(prefix="motionai_"))
    try:
        src = work / ("in_" + audio.name.replace(" ", "_"))
        src.write_bytes(audio.getvalue())
        dur = audio_duration(str(src))
        if dur > 180:
            st.warning("الملف أطول من 3 دقائق؛ الاستضافة المجانية قد لا تتحمل ذلك. يفضّل التقسيم.")
        bar = st.progress(0.0, text="تفريغ الصوت…")
        if key.strip():
            code = {"تلقائي": None, "العربية": "ar", "English": "en"}[lang]
            words, text = transcribe_groq(str(src), key, code, str(work))
        elif manual.strip():
            words = words_from_text(manual, dur)
            text = manual
        else:
            st.error("أدخل مفتاح Groq المجاني أو الصق نص الكلام.")
            st.stop()
        st.session_state["text"] = text
        opts = {"signature": signature}
        if bg_img:
            (work / "bg.png").write_bytes(bg_img.getvalue())
            opts["bg_image"] = str(work / "bg.png")
        if pres_img:
            (work / "pres.png").write_bytes(pres_img.getvalue())
            opts["presenter"] = str(work / "pres.png")
        size = (1080, 1920) if quality.startswith("1080") else (720, 1280)
        out = work / "motion.mp4"
        render(str(src), words, style, opts, str(out), work / "chunks", size, fps, 15,
               lambda p, m: bar.progress(min(p, 1.0), text=m))
        st.session_state["video"] = out.read_bytes()
        bar.progress(1.0, text="اكتمل ✅")
    except Exception as e:
        st.error(f"حدث خطأ: {e}")
    finally:
        shutil.rmtree(work, ignore_errors=True)

if "video" in st.session_state:
    st.video(st.session_state["video"])
    st.download_button("⬇️ تحميل الفيديو", st.session_state["video"], "motion.mp4", "video/mp4")
    with st.expander("النص المُفرَّغ"):
        st.write(st.session_state.get("text", ""))
