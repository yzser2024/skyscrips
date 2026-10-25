#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓 yf04.com 的 jbbs.cgi 留言板全部历史快照（Wayback）。
用于提取 2005 年前后 ONE's / With R 留言板上的留言者与他们的网站。
"""

import json
import os
import re
import time

import requests

CDX = "https://web.archive.org/cdx/search/cdx"
WB = "https://web.archive.org/web"
OUT = "out"
TARGET = "yf04.com/cgi-bin/jbbs/jbbs.cgi"

os.makedirs(OUT, exist_ok=True)
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (compatible; personal-archive/1.0)"})


def cdx(url, match="prefix", limit=3000):
    try:
        r = S.get(CDX, params={
            "url": url, "matchType": match, "output": "json",
            "fl": "timestamp,original,statuscode,length",
            "filter": "statuscode:200",
            "collapse": "urlkey",
            "limit": str(limit),
        }, timeout=240)
        if r.status_code != 200 or not r.text.strip():
            print("CDX →", r.status_code, r.text[:100], flush=True)
            return []
        rows = r.json()
        return rows[1:] if rows else []
    except Exception as e:
        print("CDX 异常", repr(e)[:150], flush=True)
        return []


rows = cdx(TARGET + "*")
print("原始快照条目：%d" % len(rows), flush=True)

# 只保留 oneyunn 板（和少量无 id 的入口页）
picked = []
for ts, orig, code, length in rows:
    low = orig.lower()
    if "id=oneyunn" in low or low.rstrip("/").endswith("jbbs.cgi"):
        picked.append((ts, orig))
print("筛选后：%d" % len(picked), flush=True)

for ts, orig in picked:
    name = re.sub(r"[^0-9a-zA-Z]+", "_", orig.split("jbbs.cgi", 1)[-1])[:60].strip("_")
    dst = os.path.join(OUT, "%s__%s.html" % (ts, name or "index"))
    if os.path.exists(dst) and os.path.getsize(dst) > 500:
        continue
    ok = False
    for attempt in range(3):
        try:
            r = S.get("%s/%sid_/%s" % (WB, ts, orig), timeout=120)
        except Exception as e:
            print("  异常", ts, repr(e)[:90], flush=True)
            time.sleep(4)
            continue
        if r.status_code == 200 and len(r.content) > 500:
            open(dst, "wb").write(r.content)
            print("  %s %s %d bytes" % (ts, orig[:80], len(r.content)), flush=True)
            ok = True
            break
        time.sleep(3)
    if not ok:
        print("  失败", ts, orig[:80], flush=True)
    time.sleep(0.6)

files = sorted(os.listdir(OUT))
print("完成：%d 个文件" % len(files), flush=True)
json.dump(files, open(os.path.join(OUT, "_index.json"), "w"), indent=1)
