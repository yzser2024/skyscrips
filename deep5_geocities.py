#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第五轮：挖 music.geocities.jp/withr17/ 全站，重点 diary/ 目录。

线索：rocketbbs oneday 板最早的条目（2008-09-30）写着「日記をかえてみましたー。
今までちょっとめんどくさいやり方だったんで」，配图 src 是
http://music.geocities.jp/withr17/diary/1.jpg ——说明 2008 年之前是手写静态日记页。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep5"
CDX = "http://web.archive.org/cdx/search/cdx"
UA = {"User-Agent": "Mozilla/5.0 (research)"}

SITES = [
    ("w17", "music.geocities.jp/withr17/"),
    ("w79", "www.geocities.jp/withr79/"),
    ("w79b", "geocities.jp/withr79/"),
    ("cl", "oneyunn79.client.jp/"),
]


def cdx(url, match="prefix", limit=900, collapse=None, filt=None):
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


def grab(ts, url, dest, minlen=200):
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


def slug(url):
    p = urllib.parse.urlparse(url)
    s = (p.path or "/").strip("/").replace("/", "_")
    if p.query:
        s += "__" + re.sub(r"[^A-Za-z0-9=_.-]", "", p.query)[:60]
    return s or "index"


def main():
    os.makedirs(OUT, exist_ok=True)
    summary = {}

    for tag, base in SITES:
        rows = cdx(base, collapse="urlkey", limit=900)
        print("##", tag, base, "URL 形态", len(rows))
        urls = []
        for ts, orig, sc, mt, ln, dg in rows:
            if sc != "200":
                continue
            urls.append((orig, mt, ln))
        textlike = [u for u in urls if ("html" in (u[1] or "")) or u[0].lower().endswith(("/", ".html", ".htm", ".cgi", ".shtml"))]
        print("  可抓页面", len(textlike), "/", len(urls))
        for orig, mt, ln in sorted(textlike):
            print("   ", orig[:110])
        summary[tag] = [u[0] for u in textlike]

        # 抓：每个 URL 取最新一份 200
        for orig, mt, ln in sorted(textlike):
            h = cdx(orig, match="exact", limit=60)
            h = [r for r in h if r[2] == "200"]
            if not h:
                continue
            h.sort(key=lambda r: r[0], reverse=True)
            ts = h[0][0]
            dest = os.path.join(OUT, tag, "%s__%s" % (slug(orig), ts))
            grab(ts, orig, dest, minlen=300)

    json.dump(summary, open(os.path.join(OUT, "urls.json"), "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
