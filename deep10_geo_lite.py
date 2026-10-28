#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十轮：轻量版。只列目录、只抓关键页，避免像上一轮那样卡满一小时。

上一轮 deep-5 对每个 URL 又做一次 exact 查询，几百个请求直接超时。
这轮改成：一次 prefix 查询拿全清单（含最新时间戳），只抓 html，限制数量。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep10"
CDX = "http://web.archive.org/cdx/search/cdx"
UA = {"User-Agent": "Mozilla/5.0 (research)"}

SITES = [
    ("w17", "music.geocities.jp/withr17/"),
    ("w79", "www.geocities.jp/withr79/"),
    ("cl", "oneyunn79.client.jp/"),
]


def cdx_prefix(url, limit=700):
    """一次拿到 URL + 每条的 timestamp，collapse 到 urlkey 会丢时间，
    但这里用 digest 去重保时间平均分布。"""
    p = {"url": url, "output": "json", "matchType": "prefix",
         "fl": "timestamp,original,statuscode,mimetype,length",
         "limit": str(limit), "collapse": "urlkey"}
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
            time.sleep(8)
    return []


def grab(ts, url, dest, minlen=400):
    u = "https://web.archive.org/web/%sid_/%s" % (ts, url)
    for i in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=45) as r:
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
        s += "__" + re.sub(r"[^A-Za-z0-9=_.-]", "", p.query)[:40]
    return (s or "index")[:80]


def main():
    os.makedirs(OUT, exist_ok=True)
    report = {}
    for tag, base in SITES:
        rows = cdx_prefix(base)
        print("##", tag, base, len(rows))
        pages = []
        for ts, orig, sc, mt, ln in rows:
            if sc != "200":
                continue
            low = orig.lower()
            if not re.search(r"(\.html?$|/$|\.cgi|\.shtml|/diary)", low):
                continue
            pages.append((ts, orig, int(ln or 0)))
        print("   页面", len(pages))
        for ts, orig, ln in pages:
            print("   %s %7d %s" % (ts, ln, orig[:100]))
        report[tag] = [p[1] for p in pages]

        # 抓：优先 diary 相关，再抓其它，最多 70 个
        pages.sort(key=lambda x: (0 if "diary" in x[1].lower() else 1, -x[2]))
        n = 0
        for ts, orig, ln in pages[:70]:
            d = os.path.join(OUT, tag, "%s__%s" % (slug(orig), ts))
            if grab(ts, orig, d):
                n += 1
        print("   抓下", n)

    json.dump(report, open(os.path.join(OUT, "urls.json"), "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
