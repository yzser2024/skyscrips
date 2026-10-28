#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第九轮：FC2 首页的「滚动窗口」。

Wayback 里 FC2 的月份归档只有 Y=2004，但博客首页 /oneyunn79/ 在 2005-2008 年
应该还有别的快照。每一份首页显示的是「当时最新的几篇」，
把不同时间点的首页叠起来，就能补上 2004-12 之后那几年的日记。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep9"
CDX = "http://web.archive.org/cdx/search/cdx"
UA = {"User-Agent": "Mozilla/5.0 (research)"}

BASES = [
    "http://diary1.fc2.com/cgi-sys/ed.cgi/oneyunn79/",
    "http://diary1.fc2.com/cgi-sys/ed.cgi/oneyunn79/?all=1",
]


def cdx(url, limit=600):
    p = {"url": url, "output": "json", "matchType": "exact",
         "fl": "timestamp,original,statuscode,mimetype,length,digest",
         "limit": str(limit)}
    u = CDX + "?" + urllib.parse.urlencode(p)
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90) as r:
                b = r.read()
            if not b.strip():
                return []
            d = json.loads(b)
            return d[1:] if d else []
        except Exception:
            time.sleep(6)
    return []


def grab(ts, url, dest, minlen=500):
    u = "https://web.archive.org/web/%sid_/%s" % (ts, url)
    for i in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=50) as r:
                b = r.read()
            if len(b) < minlen:
                return 0
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(b)
            return len(b)
        except Exception:
            time.sleep(2)
    return 0


def main():
    os.makedirs(OUT, exist_ok=True)
    allrows = []
    for base in BASES:
        rows = [r for r in cdx(base) if r[2] == "200"]
        print("##", base, len(rows), "份快照")
        years = sorted({r[0][:4] for r in rows})
        print("   年份", years)
        for ts, orig, sc, mt, ln, dg in sorted(rows):
            print("   ", ts, ln)
        allrows += rows

    # 去重（同 timestamp 同 URL）
    seen = set()
    uniq = []
    for ts, orig, sc, mt, ln, dg in sorted(allrows):
        k = (ts, orig)
        if k in seen:
            continue
        seen.add(k)
        uniq.append((ts, orig))
    print("去重后", len(uniq))

    ok = 0
    for ts, orig in uniq:
        dest = os.path.join(OUT, "home", "%s.html" % ts)
        n = grab(ts, orig, dest)
        if n:
            ok += 1
            print("   saved", ts, n)
    print("抓下", ok, "/", len(uniq))


if __name__ == "__main__":
    main()
