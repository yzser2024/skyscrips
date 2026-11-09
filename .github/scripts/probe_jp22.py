#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二十二轮：MIDI 音频文件的 Wayback 存档清点

A. 多域 CDX 全量（不 collapse，不 filter，避免 504），本地筛 .mid/.mp3
B. 对找到的音频 URL 试下载 id_ 原始件
C. 顺带查 sakuramml / 紫桜 相关存档
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

OUT = "out_jp22"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp22.txt"), "w", encoding="utf-8")


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
BUDGET = 1300


def get(url, save=None, timeout=90):
    if time.time() - T0 > BUDGET:
        return "SKIP", b""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})
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
        p = save if os.path.isabs(save) or save.startswith("out_") else os.path.join(RAW, save)
        open(p, "wb").write(b)
    return st, b


CDX = "https://web.archive.org/cdx/search/cdx"
DOMAINS = [
    ("fc2", "tristeza.web.fc2.com", "domain"),
    ("geo", "www.geocities.jp/wlstz3635", "prefix"),
    ("geo2", "www.geocities.jp/tristeza3635", "prefix"),
]
allrows = []
log("=== A. 多域 CDX 全量 ===")
for tag, dom, mt in DOMAINS:
    p = {"url": dom, "matchType": mt, "output": "json",
         "fl": "timestamp,original,statuscode,mimetype,length,digest",
         "limit": "30000"}
    u = CDX + "?" + urllib.parse.urlencode(p)
    st, b = get(u, save="cdx_%s.json" % tag, timeout=120)
    txt = b.decode("utf-8", "replace")
    rows = []
    try:
        rows = json.loads(txt)
    except Exception:
        pass
    log("%-6s %-4s rows=%d bytes=%d" % (tag, st, len(rows), len(b)))
    if rows:
        allrows.extend([[tag] + list(r) for r in rows[1:]])
    time.sleep(3)

log("")
log("=== A2. 筛选音频类 URL ===")
AUD = re.compile(r'\.(mid|midi|mp3|wav|m4a|ogg|aac|au|mp2|rm|ram|wma)(\?|#|$)|\.(mid|midi|mp3|wav)$', re.I)
audio = [r for r in allrows if AUD.search(str(r[2])) or (len(r) > 4 and r[4] and "audio" in str(r[4]))]
log("音频候选", len(audio))
for r in audio[:80]:
    log("  ", r[0], r[1], r[3], r[4], r[5] if len(r) > 5 else "", str(r[2])[:110])
json.dump(audio, open(os.path.join(OUT, "audio_cdx.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

log("")
log("=== B. 试下载 Wayback 音频原始件（去重后最多 60 个）===")
uniq = {}
for r in audio:
    u = str(r[2])
    ts = str(r[1])
    # 取每个 URL 最新一次快照
    if u not in uniq or ts > uniq[u][0]:
        uniq[u] = (ts, r)
log("去重后", len(uniq))
ok = 0
MID = os.path.join(OUT, "mid")
os.makedirs(MID, exist_ok=True)
for i, (u, (ts, r)) in enumerate(sorted(uniq.items())[:60]):
    wb = "https://web.archive.org/web/%sid_/%s" % (ts, u)
    fn = os.path.join(MID, "%03d_%s" % (i, re.sub(r'[^A-Za-z0-9_.-]', '_', u.split("/")[-1])[:60]))
    st, b = get(wb, save=fn, timeout=90)
    good = st == 200 and len(b) > 1000
    if good:
        ok += 1
    log("  %03d %-4s %8dB %s %s" % (i, st, len(b), "OK" if good else "--", u[:100]))
    if not good and os.path.exists(fn) and len(b) < 1000:
        os.remove(fn)
    time.sleep(2)

log("下载成功", ok)
fs = sorted(f for f in os.listdir(MID) if os.path.isfile(os.path.join(MID, f)))
if fs:
    with zipfile.ZipFile(os.path.join(OUT, "mid_archive.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for f in fs:
            z.write(os.path.join(MID, f), arcname=os.path.join("mid", f))
    log("mid_archive.zip", len(fs))
json.dump(allrows, open(os.path.join(OUT, "all_cdx.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("done in %ds" % int(time.time() - T0))
