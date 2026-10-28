#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""关键单页速取：只抓几个最能说明问题的入口页，几十秒内出结果。
不铺全站，避免和大任务抢时间。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_quick"
CDX = "http://web.archive.org/cdx/search/cdx"

PAGES = [
    ("rb610_withr", "http://www1.rocketbbs.com/610/withr.html"),
    ("rb651_oneday", "http://www5.rocketbbs.com/651/oneday.html"),
    ("amor_index", "http://www.geocities.jp/amorxxx79/"),
    ("withr79_index", "http://www.geocities.jp/withr79/"),
    ("withr17_index", "http://music.geocities.jp/withr17/"),
    ("yellow_index", "http://yellow.ribbon.to/~withr/"),
    ("rico1", "http://music.geocities.jp/withr17/images/rico1.jpg"),
]

QUERIES = [
    ("hjbbs_oneyunn", "yf04.com/cgi-bin/hjbbs/jbbs.cgi?id=oneyunn"),
    ("jbbs_oneyunn", "yf04.com/cgi-bin/jbbs/jbbs.cgi?id=oneyunn"),
    ("rb651_oneyunn", "www5.rocketbbs.com/651/bbs.cgi?id=oneyunn"),
    ("rb610_oneyunn", "www1.rocketbbs.com/610/bbs.cgi?id=oneyunn"),
]


def cdx(q, limit=2000):
    p = {"url": q, "output": "json", "matchType": "prefix",
         "fl": "timestamp,original,statuscode,mimetype,length",
         "collapse": "urlkey", "limit": str(limit)}
    u = CDX + "?" + urllib.parse.urlencode(p)
    for i in range(4):
        try:
            with urllib.request.urlopen(u, timeout=70) as r:
                b = r.read()
            if not b.strip():
                return []
            d = json.loads(b)
            return d[1:] if d else []
        except Exception as e:
            print("  retry", i, type(e).__name__, flush=True)
            time.sleep(6)
    return []


def grab(ts, url, dest):
    u = "https://web.archive.org/web/%sid_/%s" % (ts, url)
    for i in range(2):
        try:
            with urllib.request.urlopen(u, timeout=45) as r:
                b = r.read()
            if len(b) < 100:
                return 0
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(b)
            return len(b)
        except Exception:
            time.sleep(2)
    return 0


def main():
    os.makedirs(OUT, exist_ok=True)
    for tag, url in PAGES:
        rows = cdx(url, 400)
        ok = [r for r in rows if r[2] == "200"]
        print("== %-14s cdx %-4d 200 %-4d %s" % (tag, len(rows), len(ok), url), flush=True)
        if not ok:
            continue
        for ts, orig, sc, mt, ln in ok[-3:]:
            ext = ".html"
            if re.search(r"\.(jpg|gif|png)$", url, re.I):
                ext = os.path.splitext(url)[1]
            dest = "%s/%s/%s%s" % (OUT, tag, ts, ext)
            n = grab(ts, orig, dest)
            print("   ", ts, n, dest, flush=True)
            break
    for tag, q in QUERIES:
        rows = cdx(q, 2000)
        ok = [r for r in rows if r[2] == "200"]
        print("== %-14s cdx %-4d 200 %-4d %s" % (tag, len(rows), len(ok), q), flush=True)
        json.dump(rows, open("%s/%s.json" % (OUT, tag), "w"), ensure_ascii=False)
        if ok:
            print("    时间 %s .. %s" % (ok[0][0][:8], ok[-1][0][:8]), flush=True)
            for r in ok[:5]:
                print("    ", r[0], r[1][:100], flush=True)
            n = grab(ok[-1][0], ok[-1][1], "%s/%s/%s.html" % (OUT, tag, ok[-1][0]))
            print("    末页抓取", n, flush=True)


if __name__ == "__main__":
    main()
