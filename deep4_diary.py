#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第四轮：把 ⑨ oneday 日记板「按快照时间」全量收一遍。

思路：oneday.html 的每一份快照，内容都是「当时最新的 10 条」。
时间点取多了，这些滚动窗口就能拼出完整时间线，比只按 page=N 找更有效。
另外把 651 板下所有带 id=oneday 的 URL 形态都列出来，看有没有别的入口。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep4"
CDX = "http://web.archive.org/cdx/search/cdx"
UA = {"User-Agent": "Mozilla/5.0 (research; contact via gh)"}


def cdx(url, match="exact", limit=400, filt=None, collapse=None):
    p = {"url": url, "output": "json", "matchType": match,
         "fl": "timestamp,original,statuscode,mimetype,length,digest",
         "limit": str(limit)}
    if filt:
        p["filter"] = filt
    if collapse:
        p["collapse"] = collapse
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


def grab(ts, url, dest):
    u = "https://web.archive.org/web/%sid_/%s" % (ts, url)
    for i in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=50) as r:
                b = r.read()
            if len(b) < 200:
                return 0
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(b)
            return len(b)
        except Exception:
            time.sleep(2)
    return 0


def main():
    os.makedirs(OUT, exist_ok=True)
    report = {}

    # ---- 1. 651 板下所有 URL 形态（按 urlkey 折叠）----
    rows = cdx("www5.rocketbbs.com/651/", match="prefix", limit=600,
               collapse="urlkey")
    print("651 前缀 URL 形态", len(rows))
    forms = {}
    for ts, orig, sc, mt, ln, dg in rows:
        key = urllib.parse.urlparse(orig).path + (
            "?" + urllib.parse.urlparse(orig).query if urllib.parse.urlparse(orig).query else "")
        forms.setdefault(key, []).append(ts)
    for k in sorted(forms):
        print("   %-46s %d 份快照" % (k[:46], len(forms[k])))
    report["forms"] = {k: sorted(v) for k, v in forms.items()}

    # ---- 2. oneday.html 的全部快照（滚动窗口）----
    snaps = cdx("www5.rocketbbs.com/651/oneday.html", match="exact", limit=400)
    snaps = [r for r in snaps if r[2] == "200"]
    snaps.sort(key=lambda r: r[0])
    print("oneday.html 快照", len(snaps))
    got = 0
    for ts, orig, sc, mt, ln, dg in snaps:
        dest = os.path.join(OUT, "oneday_html", "%s.html" % ts)
        n = grab(ts, orig, dest)
        if n:
            got += 1
            print("   %s -> %d" % (ts, n))
    print("oneday.html 抓到", got, "/", len(snaps))

    # ---- 3. 带 id=oneday 的所有 bbs.cgi 快照 ----
    brows = cdx("www5.rocketbbs.com/651/bbs.cgi", match="prefix", limit=800)
    oned = [r for r in brows if "id=oneday" in r[1]]
    print("id=oneday 相关快照", len(oned))
    pairs = set()
    for ts, orig, sc, mt, ln, dg in oned:
        if sc != "200":
            continue
        q = urllib.parse.parse_qs(urllib.parse.urlparse(orig).query)
        page = (q.get("page") or ["1"])[0]
        pairs.add((page, ts, orig))
    print("去重后", len(pairs))
    ok = 0
    for page, ts, orig in sorted(pairs):
        dest = os.path.join(OUT, "oneday_pages", "p%02d__%s.html" % (int(page), ts))
        n = grab(ts, orig, dest)
        if n:
            ok += 1
            print("   page%02d %s -> %d" % (int(page), ts, n))
    print("分页抓到", ok, "/", len(pairs))

    json.dump(report, open(os.path.join(OUT, "report.json"), "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
