#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第三轮：抓 ⑨ oneday 日记的全部分页（2004-2011），
① withr 留言板的全部分页（20 页），⑦ amorxxx79 别馆全站。
oneday 与 withr 的板 id 是 id=oneday / id=withr，不是 oneyunn。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep3"
CDX = "http://web.archive.org/cdx/search/cdx"


def cdx(url, limit=200):
    p = {"url": url, "output": "json", "matchType": "exact",
         "fl": "timestamp,original,statuscode,mimetype,length,digest",
         "limit": str(limit)}
    u = CDX + "?" + urllib.parse.urlencode(p)
    for i in range(4):
        try:
            with urllib.request.urlopen(u, timeout=70) as r:
                b = r.read()
            if not b.strip():
                return []
            d = json.loads(b)
            return d[1:] if d else []
        except Exception:
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


def fetch(url, dest, prefer_latest=True):
    rows = [r for r in cdx(url) if r[2] == "200"]
    if not rows:
        return 0
    rows.sort(key=lambda r: r[0], reverse=prefer_latest)
    for ts, orig, sc, mt, ln, dg in rows[:3]:
        n = grab(ts, orig, "%s__%s" % (dest, ts))
        if n:
            return n
    return 0


def main():
    os.makedirs(OUT, exist_ok=True)
    log = []

    # 1) oneday 日记：page 1..20 + RSS
    for pg in range(1, 21):
        u = "http://www5.rocketbbs.com/651/bbs.cgi?id=oneday&page=%d" % pg
        n = fetch(u, "%s/oneday/p%02d.html" % (OUT, pg))
        print("oneday p%d -> %d" % (pg, n), flush=True)
        log.append(("oneday", pg, n))
    for rss in ("http://www5.rocketbbs.com/651/rss/oneday.rdf",
                "http://www5.rocketbbs.com/651/bbs.cgi?id=oneday"):
        n = fetch(rss, "%s/oneday/%s" % (OUT, re.sub(r"[^0-9A-Za-z]+", "_", rss)[-30:]))
        print("oneday extra", rss, n, flush=True)

    # 2) withr 留言板：page 1..20
    for pg in range(1, 21):
        u = "http://www1.rocketbbs.com/610/bbs.cgi?id=withr&page=%d" % pg
        n = fetch(u, "%s/withr/p%02d.html" % (OUT, pg))
        print("withr p%d -> %d" % (pg, n), flush=True)
        log.append(("withr", pg, n))

    # 3) amorxxx79 别馆全站
    rows = cdx("http://www.geocities.jp/amorxxx79/", 2000)
    rows = [r for r in rows if r[2] == "200" and r[3] and "html" in r[3]]
    print("amor html", len(rows), flush=True)
    got = 0
    for ts, orig, sc, mt, ln, dg in rows:
        rel = urllib.parse.urlparse(orig).path.strip("/").replace("/", "_") or "index"
        dest = "%s/amor/%s__%s.html" % (OUT, ts, re.sub(r"[^0-9A-Za-z._-]+", "-", rel))
        if os.path.exists(dest):
            continue
        if grab(ts, orig, dest):
            got += 1
    print("amor 抓取", got, flush=True)

    json.dump(log, open(OUT + "/log.json", "w"))


if __name__ == "__main__":
    main()
