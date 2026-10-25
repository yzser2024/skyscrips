#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 Wayback Machine 抓 ucaliy.tumblr.com 的历史首页快照（按月去重）。
Tumblr 自家反爬会 403 掉直接抓取，但档案馆存的是当年服务端渲染的完整 HTML。
"""

import json
import os
import time

import requests

BLOG = "ucaliy.tumblr.com"
OUT = "out"
CDX = "https://web.archive.org/cdx/search/cdx"
WB = "https://web.archive.org/web"

os.makedirs(OUT, exist_ok=True)
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (compatible; personal-archive/1.0)"})


def cdx(url, collapse="timestamp:6", limit=300):
    try:
        r = S.get(CDX, params={
            "url": url, "output": "json",
            "fl": "timestamp,original,statuscode",
            "filter": "statuscode:200",
            "collapse": collapse, "limit": limit,
        }, timeout=180)
        if r.status_code != 200 or not r.text.strip():
            print("  CDX", url, "→", r.status_code, flush=True)
            return []
        rows = r.json()
        return rows[1:] if rows else []
    except Exception as e:
        print("  CDX 失败", url, repr(e)[:120], flush=True)
        return []


def grab(ts, orig, tag):
    dst = os.path.join(OUT, "%s_%s.html" % (tag, ts))
    if os.path.exists(dst) and os.path.getsize(dst) > 2000:
        return True
    for attempt in range(3):
        try:
            r = S.get("%s/%sid_/%s" % (WB, ts, orig), timeout=120)
        except Exception as e:
            print("    抓取异常", ts, repr(e)[:100], flush=True)
            time.sleep(4 * (attempt + 1))
            continue
        if r.status_code == 200 and len(r.content) > 2000:
            open(dst, "wb").write(r.content)
            print("  %s %s  %d bytes" % (tag, ts, len(r.content)), flush=True)
            return True
        time.sleep(3 * (attempt + 1))
    print("  %s %s 失败" % (tag, ts), flush=True)
    return False


print("== 1. 首页按月快照 ==", flush=True)
rows = cdx(BLOG + "/")
print("  找到 %d 个月度快照" % len(rows), flush=True)
for ts, orig, code in rows:
    grab(ts, orig, "home")
    time.sleep(0.8)

print("== 2. 分页快照 ==", flush=True)
for p in range(2, 9):
    rows2 = cdx("%s/page/%d" % (BLOG, p), collapse="timestamp:6", limit=60)
    if not rows2:
        print("  page/%d 无快照" % p, flush=True)
        continue
    print("  page/%d 有 %d 条快照" % (p, len(rows2)), flush=True)
    for ts, orig, code in rows2:
        grab(ts, orig, "p%d" % p)
        time.sleep(0.8)

files = [f for f in os.listdir(OUT) if f.endswith(".html")]
print("== 完成：%d 个页面 ==" % len(files), flush=True)
json.dump(files, open(os.path.join(OUT, "index.json"), "w"), indent=1)
