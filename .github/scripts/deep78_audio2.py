#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精简音频普查：只查四个关键域名，每个一次请求，短退避。"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_deep78"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research; withr-archive)"}
RX = r".*\.(mp3|mid|midi|wav|wma|ogg|m4a)$"


def get(url, tries=3, timeout=75):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            print("HTTP", e.code, flush=True)
            if e.code in (429, 503, 502, 504):
                time.sleep(12 + i * 12)
                continue
            if e.code in (404, 403):
                return None
        except Exception as e:
            print("ERR", type(e).__name__, flush=True)
            time.sleep(6)
    return None


prefixes = [
    "music.geocities.jp/withr17/",
    "www.geocities.jp/amorxxx79/",
    "www.geocities.jp/oneyunn79/",
    "withr.y.ribbon.to/",
]
res = {}
for p in prefixes:
    q = ("http://web.archive.org/cdx/search/cdx?url=%s&matchType=prefix&output=json"
         "&fl=original,timestamp,statuscode,length&filter=original:%s"
         "&collapse=urlkey&limit=300"
         % (urllib.parse.quote(p, safe=""), urllib.parse.quote(RX, safe=".*()|")))
    b = get(q)
    rows = []
    if b:
        try:
            d = json.loads(b.decode("utf-8", "replace"))
            rows = d[1:] if d else []
        except Exception as e:
            print("PARSE", e, b[:120], flush=True)
    res[p] = rows
    print("==", p, len(rows), flush=True)
    for x in rows[:40]:
        print("   ", x, flush=True)
    time.sleep(3.0)

json.dump(res, open(os.path.join(OUT, "audio_cdx.json"), "w"), ensure_ascii=False, indent=1)
print("done")
