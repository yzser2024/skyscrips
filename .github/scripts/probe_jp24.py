#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二十四轮：下载 note-sound 全部 89 首音频

对每个 sound key：
  1. GET https://note.com/api/v3/sounds/<key>  -> play_url (签名 mp3)
  2. GET play_url -> mp3，按 序号_曲名.mp3 命名
分卷每卷 15 首，另存元数据 JSON。
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
import zipfile

OUT = "out_jp24"
os.makedirs(OUT, exist_ok=True)
AUD = os.path.join(OUT, "mp3")
os.makedirs(AUD, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp24.txt"), "w", encoding="utf-8")


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

SOUNDS = json.load(open(os.path.join(os.path.dirname(__file__), "sounds.json"),
                        encoding="utf-8"))


def get(url, timeout=60):
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
    return st, b


def safe(s):
    return re.sub(r'[^\w\u3040-\u30ff\u4e00-\u9fff.\-]+', "_", s).strip("_")[:60]


metadata = []
ok = 0
for idx, (name, sid) in enumerate(SOUNDS):
    api = "https://note.com/api/v3/sounds/%s" % sid
    st, b = get(api, timeout=45)
    play_url = None
    info = {}
    if st == 200:
        try:
            d = json.loads(b.decode("utf-8", "replace"))["data"]
            play_url = d.get("play_url")
            info = {"key": sid, "title": d.get("title"), "artist": d.get("artist_name"),
                    "original_filename": d.get("original_filename"),
                    "duration": d.get("duration"), "downloadable": d.get("downloadable")}
        except Exception as e:
            log("%03d %-30s api json fail %s" % (idx, name[:30], e))
    rec = {"idx": idx, "name": name, "sound_id": sid, "api_status": st, **info}
    if not play_url:
        log("%03d %-32s api=%s no play_url" % (idx, name[:32], st))
        metadata.append(rec)
        time.sleep(0.3)
        continue
    st2, mp3 = get(play_url, timeout=90)
    good = st2 == 200 and len(mp3) > 8000
    if good:
        fn = os.path.join(AUD, "%03d_%s.mp3" % (idx, safe(name)))
        open(fn, "wb").write(mp3)
        ok += 1
        rec["file"] = os.path.basename(fn)
        rec["bytes"] = len(mp3)
    log("%03d %-32s api=%s mp3=%s %sB dur=%s %s" % (
        idx, name[:32], st, st2, len(mp3), info.get("duration"),
        "OK" if good else "FAIL"))
    rec["mp3_status"] = st2
    rec["mp3_bytes"] = len(mp3)
    metadata.append(rec)
    time.sleep(0.4)

json.dump(metadata, open(os.path.join(OUT, "sounds_meta.json"), "w",
                         encoding="utf-8"), ensure_ascii=False, indent=1)
log("downloaded", ok, "of", len(SOUNDS))

fs = sorted(f for f in os.listdir(AUD) if f.endswith(".mp3"))
log("audio files", len(fs))
for i in range(0, len(fs), 15):
    zn = os.path.join(OUT, "snd_vol%d.zip" % (i // 15 + 1))
    with zipfile.ZipFile(zn, "w", zipfile.ZIP_STORED) as z:
        for f in fs[i:i + 15]:
            z.write(os.path.join(AUD, f), arcname=os.path.join("mp3", f))
    log("  ", os.path.basename(zn), len(fs[i:i + 15]))
with zipfile.ZipFile(os.path.join(OUT, "snd_meta.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    z.write(os.path.join(OUT, "sounds_meta.json"), arcname="sounds_meta.json")
    z.write(os.path.join(OUT, "log_jp24.txt"), arcname="log_jp24.txt")
log("done in %ds" % int(time.time() - T0))
