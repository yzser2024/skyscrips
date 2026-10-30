#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓 withr17/ld 已存档的章节页原文（02/03/04/07/08/11）与 ld11 的 2012 快照。"""
import os
import time
import urllib.error
import urllib.request

OUT = "out_deep72"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research; withr-archive)"}

JOBS = [
    ("ld02", "http://music.geocities.jp/withr17/ld/ld02.html", "20111103122453"),
    ("ld03", "http://music.geocities.jp/withr17/ld/ld03.html", "20111103122536"),
    ("ld04", "http://music.geocities.jp/withr17/ld/ld04.html", "20111103122555"),
    ("ld07", "http://music.geocities.jp/withr17/ld/ld07.html", "20111102162431"),
    ("ld08", "http://music.geocities.jp/withr17/ld/ld08.html", "20111103122613"),
    ("ld11", "http://music.geocities.jp/withr17/ld/ld11.html", "20111102162544"),
    ("wsg2011", "http://music.geocities.jp/withr17/wsg.html", "20111103122731"),
    ("ld_top", "http://music.geocities.jp/withr17/ld/top.html", "20111102162412"),
    ("ld_info", "http://music.geocities.jp/withr17/ld/info.html", "20111102162508"),
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
    time.sleep(1.5)
print("done")
