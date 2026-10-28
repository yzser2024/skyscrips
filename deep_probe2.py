#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二轮深挖：精确到板 id 的 CDX 普查 + 原文抓取。
上一轮用 prefix 查整个 610/651/310，结果被别人的板挤满 4000 条上限，
yukari 自己的条目一条都没剩下。这轮直接按 ?id=oneyunn 查。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep2"
CDX = "http://web.archive.org/cdx/search/cdx"

# (标签, 查询 URL, matchType)
QUERIES = [
    ("rb610_bbs", "www1.rocketbbs.com/610/bbs.cgi?id=oneyunn", "prefix"),
    ("rb610_top", "www1.rocketbbs.com/610/withr.html", "exact"),
    ("rb651_oneday", "www5.rocketbbs.com/651/oneday.html", "exact"),
    ("rb651_bbs", "www5.rocketbbs.com/651/bbs.cgi?id=oneyunn", "prefix"),
    ("rb310_bbs", "www1.rocketbbs.com/310/bbs.cgi?id=oneyunn", "prefix"),
    ("yf04_bbs", "yf04.com/cgi-bin/bbs.cgi", "prefix"),
    ("yf04_gb", "yf04.com/cgi-bin/gb.cgi", "prefix"),
    ("yf04_hjbbs", "yf04.com/cgi-bin/hjbbs/jbbs.cgi", "prefix"),
    ("geo_amor", "www.geocities.jp/amorxxx79/", "prefix"),
    ("geo_withr79", "www.geocities.jp/withr79/", "prefix"),
    ("music_withr17", "music.geocities.jp/withr17/", "prefix"),
    ("yellow_withr", "yellow.ribbon.to/~withr/", "prefix"),
]

STATIC = {"geo_amor", "geo_withr79", "music_withr17", "yellow_withr"}
MAX_FETCH = 700


def cdx(query, mt, limit=3000):
    params = {"url": query, "output": "json", "matchType": mt,
              "fl": "timestamp,original,statuscode,mimetype,length",
              "collapse": "urlkey", "limit": str(limit)}
    u = CDX + "?" + urllib.parse.urlencode(params)
    for i in range(5):
        try:
            with urllib.request.urlopen(u, timeout=90) as r:
                b = r.read()
            if not b.strip():
                return []
            d = json.loads(b)
            return d[1:] if d else []
        except Exception as e:
            print("  cdx retry", i, type(e).__name__, flush=True)
            time.sleep(8)
    return []


def good(r):
    ts, orig, sc, mt, ln = r
    return sc == "200" and mt and ("html" in mt or "text" in mt)


def grab(ts, url, dest):
    u = "https://web.archive.org/web/%sid_/%s" % (ts, url)
    for i in range(2):
        try:
            with urllib.request.urlopen(u, timeout=45) as r:
                b = r.read()
            if len(b) < 200:
                return 0
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(b)
            return len(b)
        except Exception:
            time.sleep(2)
    return 0


def safe(url):
    s = url.split("://", 1)[1]
    s = re.sub(r"[^0-9A-Za-z._~-]+", "_", s)
    return s[:150]


def main():
    os.makedirs(OUT, exist_ok=True)
    report = []
    fetched = 0
    for tag, q, mt in QUERIES:
        rows = cdx(q, mt)
        rows = [r for r in rows if good(r)]
        print("== %-14s %-52s 可用 %d" % (tag, q[:52], len(rows)), flush=True)
        json.dump(rows, open("%s/%s_cdx.json" % (OUT, tag), "w"), ensure_ascii=False)
        if rows:
            print("   时间 %s .. %s" % (rows[0][0][:8], rows[-1][0][:8]), flush=True)
        for r in rows[:8]:
            print("   ", r[0], r[1][:100], flush=True)
        got = 0
        for ts, orig, sc, mtp, ln in rows:
            if fetched >= MAX_FETCH:
                break
            dest = "%s/%s/%s__%s.html" % (OUT, tag, ts, safe(orig))
            if os.path.exists(dest):
                continue
            n = grab(ts, orig, dest)
            if n:
                got += 1
                fetched += 1
        print("   抓取", got, flush=True)
        report.append({"tag": tag, "query": q, "rows": len(rows), "fetched": got})
    json.dump(report, open(OUT + "/report.json", "w"), ensure_ascii=False, indent=1)
    print("=== 合计抓取", fetched)


if __name__ == "__main__":
    main()
