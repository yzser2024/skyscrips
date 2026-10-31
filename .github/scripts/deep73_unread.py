#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补抓 5 个疑未读页：konokaradade、cc/r、ld/info、ld/right、ld/home。"""
import os
import time
import urllib.error
import urllib.request

OUT = "out_deep73"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research; withr-archive)"}
JOBS = [
    ("konokaradade", "http://music.geocities.jp/withr17/konokaradade.html", "20181105032118"),
    ("cc_r", "http://music.geocities.jp/withr17/cc/r.html", "20111103122634"),
    ("ld_info", "http://music.geocities.jp/withr17/ld/info.html", "20120730042735"),
    ("ld_right", "http://music.geocities.jp/withr17/ld/right.html", "20120730042650"),
    ("ld_home", "http://music.geocities.jp/withr17/ld/home.html", "20120730042649"),
    ("cc_index", "http://music.geocities.jp/withr17/cc/index.html", "20111103122632"),
    ("cc_top", "http://music.geocities.jp/withr17/cc/top.html", "20111103122633"),
]


def get(url, tries=4, timeout=60):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                time.sleep(15 + i * 15)
                continue
            if e.code == 404:
                return None
        except Exception:
            time.sleep(8)
    return None


for name, original, ts in JOBS:
    url = "http://web.archive.org/web/%sid_/%s" % (ts, original)
    b = get(url)
    if b:
        open(os.path.join(OUT, name + ".html"), "wb").write(b)
        print("ok", name, len(b), flush=True)
    else:
        print("FAIL", name, flush=True)
    time.sleep(1.2)
print("done")
