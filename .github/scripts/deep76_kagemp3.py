#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抢救 withr79/kage.mp3（CDX 显示 4.68 MB 有 4 个快照），并普查全部旧站下的音频/图片。"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_deep76"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research; withr-archive)"}


def get(url, tries=5, timeout=180):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            print("HTTP", e.code, url, flush=True)
            if e.code in (429, 503, 502, 504):
                time.sleep(20 + i * 20)
                continue
            if e.code in (404, 403):
                return None
        except Exception as e:
            print("ERR", type(e).__name__, url, flush=True)
            time.sleep(8)
    return None


def cdx(q, tries=4):
    b = get(q, tries=tries, timeout=90)
    if not b:
        return []
    try:
        d = json.loads(b.decode("utf-8", "replace"))
        return d[1:] if d else []
    except Exception:
        return []


# 1) kage.mp3 四个快照全试，取第一个成功的
snaps = ["20070714154100", "20070714154108", "20070714154110", "20070714154116"]
got = None
for ts in snaps:
    for host in ["www.geocities.jp/withr79/kage.mp3",
                 "www.geocities.jp:80/withr79/kage.mp3"]:
        url = "https://web.archive.org/web/%sid_/http://%s" % (ts, host)
        b = get(url, tries=2, timeout=300)
        print("TRY", ts, host, len(b) if b else None, flush=True)
        if b and len(b) > 100000:
            got = b
            break
    if got:
        break
if got:
    open(os.path.join(OUT, "kage.mp3"), "wb").write(got)
    print("SAVED kage.mp3", len(got), got[:4], flush=True)
else:
    print("kage.mp3 FAIL", flush=True)

# 2) 普查：所有旧域名下的 mp3 / 图片
prefixes = [
    "www.geocities.jp/withr79/", "www.geocities.jp/withr17/",
    "www.geocities.jp/amorxxx79/", "www.geocities.jp/oneyunn79/",
    "music.geocities.jp/withr17/", "music.geocities.jp/oneyunn79/",
    "withr.y.ribbon.to/~withr/", "yellow.ribbon.to/~withr/",
]
allrows = {}
for p in prefixes:
    for ext in ["mp3", "mid", "wav", "jpg", "gif", "png"]:
        q = ("http://web.archive.org/cdx/search/cdx?url=%s*.%s&output=json"
             "&fl=original,timestamp,statuscode,length&collapse=urlkey&limit=400"
             % (urllib.parse.quote(p, safe=""), ext))
        r = cdx(q, tries=3)
        if r:
            allrows[p + " *." + ext] = r
            print("FOUND", p, ext, len(r), flush=True)
            for x in r[:10]:
                print("   ", x, flush=True)
        time.sleep(1.0)

json.dump(allrows, open(os.path.join(OUT, "assets_cdx.json"), "w"),
          ensure_ascii=False, indent=1)
print("done")
