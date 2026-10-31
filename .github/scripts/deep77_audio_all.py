#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全域音频普查：所有旧站下的 mp3 / mid / wav，用 matchType=prefix + 正则 filter。"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_deep77"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research; withr-archive)"}


def get(url, tries=5, timeout=120):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                time.sleep(18 + i * 18)
                continue
            if e.code in (404, 403):
                return None
        except Exception:
            time.sleep(6)
    return None


def cdx(prefix, regex, limit=600):
    q = ("http://web.archive.org/cdx/search/cdx?url=%s&matchType=prefix&output=json"
         "&fl=original,timestamp,statuscode,length&filter=original:%s"
         "&collapse=urlkey&limit=%d"
         % (urllib.parse.quote(prefix, safe=""), urllib.parse.quote(regex, safe=".*()|"), limit))
    b = get(q, tries=4)
    if not b:
        return []
    try:
        d = json.loads(b.decode("utf-8", "replace"))
        return d[1:] if d else []
    except Exception:
        return []


prefixes = [
    "www.geocities.jp/withr79/",
    "www.geocities.jp/withr17/",
    "music.geocities.jp/withr17/",
    "www.geocities.jp/amorxxx79/",
    "www.geocities.jp/oneyunn79/",
    "www.geocities.jp/withr/",
    "withr.y.ribbon.to/",
    "yellow.ribbon.to/",
    "www1.rocketbbs.com/610/",
]
regex = r".*\.(mp3|mid|midi|wav|wma|ogg|m4a|zip|lzh)$"

allrows = {}
for p in prefixes:
    r = cdx(p, regex)
    print("==", p, len(r), flush=True)
    for x in r:
        print("   ", x, flush=True)
    allrows[p] = r
    time.sleep(2.0)

json.dump(allrows, open(os.path.join(OUT, "audio_cdx.json"), "w"),
          ensure_ascii=False, indent=1)
total = sum(len(v) for v in allrows.values())
print("TOTAL", total, flush=True)
print("done")
