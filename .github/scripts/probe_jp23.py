#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二十三轮：找 note-sound 音频的真实 API 端点

1. 抓 embed 页引用的 JS chunks（尤其 sounds/[soundKey]/page），grep API 路径
2. 对 soundKey 试各种 API 端点
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request

OUT = "out_jp23"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp23.txt"), "w", encoding="utf-8")


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


def get(url, save=None, timeout=60):
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
        open(os.path.join(RAW, save), "wb").write(b)
    return st, b


SID = "c9a78dd11d7c44262e58bfe9a9abf384"  # ティルシア
log("=== A. 抓 JS chunks ===")
chunks = [
    "https://note.com/embed/_next/static/chunks/app/sounds/%5BsoundKey%5D/page-818a778e9e3f6084.js",
    "https://note.com/embed/_next/static/chunks/782-" + "0" * 16 + ".js",
]
# 先从 embed 页解析全部 chunk 路径
st, b = get("https://note.com/embed/sounds/%s" % SID, save="embed.html")
s = b.decode("utf-8", "replace")
paths = re.findall(r'(/_next/static/chunks/[^"\']+\.js)', s)
log("chunks found", len(paths))
jsall = ""
for i, p in enumerate(dict.fromkeys(paths)):
    st, b = get("https://note.com/embed" + p, save="chunk_%02d.js" % i, timeout=60)
    txt = b.decode("utf-8", "replace")
    jsall += txt
    log("  chunk %02d %-70s %s %dB" % (i, p[-70:], st, len(b)))
    time.sleep(0.3)

open(os.path.join(RAW, "js_all.txt"), "w", encoding="utf-8").write(jsall)
log("js total", len(jsall))
log("")
log("=== B. JS 里的 API 路径 / 音频字段 ===")
pats = [r'/api/[A-Za-z0-9_/{}$.-]+', r'api/v[0-9]/[A-Za-z0-9_/{}$.-]+',
        r'sounds/[A-Za-z0-9_/${}.-]+', r'audio[A-Za-z_]{0,20}',
        r'sound[A-Za-z_]{0,20}', r'\.mp3', r'\.m4a', r'st-note', r'cdn', r'download']
for pat in pats:
    hits = list(dict.fromkeys(re.findall(pat, jsall, re.I)))
    log("  [%s] %d: %s" % (pat, len(hits), str(hits[:12])[:300]))

log("")
log("=== C. 试 API 端点 ===")
endpoints = [
    "https://note.com/api/v3/sounds/%s" % SID,
    "https://note.com/api/v2/sounds/%s" % SID,
    "https://note.com/api/v1/sounds/%s" % SID,
    "https://note.com/api/v3/sounds/%s/play" % SID,
    "https://note.com/api/v2/sounds/%s/play" % SID,
    "https://note.com/embed/api/sounds/%s" % SID,
    "https://note.com/api/v3/embedded_contents/sound/%s" % SID,
]
for i, u in enumerate(endpoints):
    st, b = get(u, save="api_%02d.json" % i)
    txt = b.decode("utf-8", "replace")
    has = any(k in txt.lower() for k in ("mp3", "m4a", "audio", "http", "url"))
    log("  %-4s %-62s %6dB has=%s  %s" % (st, u[:62], len(b), has, txt[:120].replace("\n", " ")))
    time.sleep(0.5)

log("done in %ds" % int(time.time() - T0))
