#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二十一轮：note-sound 89 首音频 —— 解析 embed 页取真实音频 URL 并下载

内嵌全部 89 个 (曲名, sound_id)。逐个抓 note.com/embed/sounds/<id>，
从 __NEXT_DATA__ / 内联 JSON 里找音频文件 URL，逐个下载为 mp3/m4a。
分卷每卷 15 个文件，便于下载。
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
import zipfile

OUT = "out_jp21"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
AUD = os.path.join(OUT, "audio")
os.makedirs(RAW, exist_ok=True)
os.makedirs(AUD, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp21.txt"), "w", encoding="utf-8")


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
T0 = time.time()
BUDGET = 1500

# 89 个 (曲名, sound_id)
SOUNDS = json.load(open(os.path.join(os.path.dirname(__file__), "sounds.json"),
                        encoding="utf-8")) if os.path.exists(
    os.path.join(os.path.dirname(__file__), "sounds.json")) else []


def get(url, save=None, timeout=50):
    if time.time() - T0 > BUDGET:
        return "SKIP", b""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "ja,en;q=0.8",
        "Referer": "https://note.com/"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            b, st = r.read(), r.status
    except urllib.error.HTTPError as e:
        try:
            b = e.read()
        except Exception:
            b = b""
        st = e.code
    except Exception as e:
        return None, ("%s: %s" % (type(e).__name__, e)).encode()
    if save:
        p = os.path.join(RAW, save) if save.startswith("embed_") else save
        open(p, "wb").write(b)
    return st, b


def safe(s):
    return re.sub(r'[^\w\u3040-\u30ff\u4e00-\u9fff.-]+', "_", s)[:60]


log("SOUNDS", len(SOUNDS))

# ---- A. 先解析前 3 个 embed 页，摸清 URL 形态 ----
URL_PATTERNS = [
    re.compile(r'https?://[^"\'<>\s\\]+\.(?:mp3|m4a|aac|ogg|wav)(?:\?[^"\'<>\s\\]*)?', re.I),
]
resolved = []
for idx, (name, sid) in enumerate(SOUNDS):
    u = "https://note.com/embed/sounds/%s" % sid
    st, b = get(u, save="embed_%03d.html" % idx)
    s = b.decode("utf-8", "replace")
    urls = []
    if idx < 3:
        open(os.path.join(RAW, "embed_sample_%d.html" % idx), "wb").write(b)
    for pat in URL_PATTERNS:
        for x in pat.findall(s):
            x = x.replace("\\u0026", "&").replace("\\/", "/").replace("&amp;", "&")
            if x not in urls:
                urls.append(x)
    # 备选：__NEXT_DATA__ 里的 audio_url / sound_url 字段
    for kw in ["audio_url", "audioUrl", "sound_url", "source_url", "file_url", "mp3"]:
        for m in re.finditer(kw, s, re.I):
            seg = s[max(0, m.start() - 20):m.start() + 260]
            mm = re.search(r'https?[^"\'<>\s\\]{20,}', seg)
            if mm:
                x = mm.group(0).replace("\\u0026", "&").replace("\\/", "/")
                if x not in urls:
                    urls.append(x)
            break
    real = [x for x in urls if not any(k in x for k in ("favicon", ".css", ".js", "ogimage"))]
    log("%03d %-34s %-4s %6dB urls=%d  %s" % (
        idx, name[:34], st, len(b), len(real), real[0][:110] if real else "-"))
    resolved.append({"idx": idx, "name": name, "sound_id": sid,
                     "embed_status": st, "urls": real})
    if idx in (0, 1, 2):
        for x in real[:3]:
            log("      ", x[:160])
    time.sleep(0.6)

json.dump(resolved, open(os.path.join(OUT, "resolved.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---- B. 下载能解析到 URL 的 ----
log("")
log("=== B. 下载 ===")
ok = 0
for r in resolved:
    if not r["urls"]:
        continue
    u = r["urls"][0]
    ext = ".mp3"
    m = re.search(r'\.(mp3|m4a|aac|ogg|wav)', u, re.I)
    if m:
        ext = "." + m.group(1).lower()
    fn = os.path.join(AUD, "%03d_%s%s" % (r["idx"], safe(r["name"]), ext))
    st, b = get(u, save=fn, timeout=90)
    if st == 200 and len(b) > 10000:
        ok += 1
        log("  OK  %03d %-30s %8dB %s" % (r["idx"], r["name"][:30], len(b), ext))
    else:
        log("  FAIL %03d %-30s %s %dB" % (r["idx"], r["name"][:30], st, len(b)))
        if os.path.exists(fn) and len(b) < 10000:
            os.remove(fn)
    time.sleep(0.4)

log("downloaded", ok)

# ---- C. 分卷 ----
fs = sorted(f for f in os.listdir(AUD) if os.path.isfile(os.path.join(AUD, f)))
log("audio files", len(fs))
for i in range(0, len(fs), 15):
    zn = os.path.join(OUT, "snd_vol%d.zip" % (i // 15 + 1))
    with zipfile.ZipFile(zn, "w", zipfile.ZIP_STORED) as z:
        for f in fs[i:i + 15]:
            z.write(os.path.join(AUD, f), arcname=os.path.join("audio", f))
    log("  ", zn, len(fs[i:i + 15]))
with zipfile.ZipFile(os.path.join(OUT, "snd_meta.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    z.write(os.path.join(OUT, "resolved.json"), arcname="resolved.json")
    z.write(os.path.join(OUT, "log_jp21.txt"), arcname="log_jp21.txt")
log("done in %ds" % int(time.time() - T0))
