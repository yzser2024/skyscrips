#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第六轮：找 2004-12 ~ 2008-09 之间缺失的日记。

已知两条线：
 · FC2 diary1.fc2.com/cgi-sys/ed.cgi/oneyunn79/ 只见到 Y=2004 的月份页
 · rocketbbs oneday 板最早到 2008-09-30，此前她写「日記をかえてみました」
所以这段的日记应该在别处：母站 yf04.com 的自建页，或 geocities 静态页。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep6"
CDX = "http://web.archive.org/cdx/search/cdx"
UA = {"User-Agent": "Mozilla/5.0 (research)"}


def cdx(url, match="prefix", limit=1500, collapse="urlkey", filt=None):
    p = {"url": url, "output": "json", "matchType": match,
         "fl": "timestamp,original,statuscode,mimetype,length,digest",
         "limit": str(limit)}
    if collapse:
        p["collapse"] = collapse
    if filt:
        p["filter"] = filt
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


def grab(ts, url, dest, minlen=300):
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
    log = []

    # ---- FC2 全量 URL ----
    rows = cdx("diary1.fc2.com/cgi-sys/ed.cgi/oneyunn79/", limit=1500)
    print("## FC2 URL 形态", len(rows))
    fc2 = []
    for ts, orig, sc, mt, ln, dg in rows:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(orig).query)
        y = (q.get("Y") or [""])[0]
        mth = (q.get("M") or [""])[0]
        fc2.append((y, mth, orig, ts, sc))
        print("   Y=%s M=%s %s %s" % (y or "-", mth or "-", sc, orig[:80]))
    years = sorted({y for y, m, o, t, s in fc2 if y})
    print("   FC2 出现过的年份:", years)

    # ---- yf04 全站目录 ----
    rows2 = cdx("yf04.com/", limit=1800)
    print("## yf04 URL 形态", len(rows2))
    dirs = {}
    for ts, orig, sc, mt, ln, dg in rows2:
        p = urllib.parse.urlparse(orig).path
        d = "/".join(p.strip("/").split("/")[:1]) or "/"
        dirs.setdefault(d, 0)
        dirs[d] += 1
    for k in sorted(dirs, key=lambda x: -dirs[x]):
        print("   %-24s %d" % (k, dirs[k]))

    cand = [(ts, orig) for ts, orig, sc, mt, ln, dg in rows2
            if sc == "200" and re.search(r"(diary|log|diary\.html|column|note)", orig, re.I)]
    print("## yf04 疑似日记页", len(cand))
    for ts, orig in cand[:60]:
        print("   ", ts, orig[:110])

    # 抓疑似日记页
    for ts, orig in cand[:80]:
        slug = re.sub(r"[^A-Za-z0-9._-]", "_", urllib.parse.urlparse(orig).path)[:70]
        grab(ts, orig, os.path.join(OUT, "yf04", "%s__%s" % (slug, ts)))

    json.dump({"fc2": fc2}, open(os.path.join(OUT, "fc2.json"), "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
