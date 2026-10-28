#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十一轮：只打「日记」这几个确切文件，确认是不是手写日记页。

CDX 已确认存在：
  music.geocities.jp/withr17/diary.html   + diary/1.jpg, diary/2.jpg
  www.geocities.jp/amorxxx79/diary.html
另有几个疑似独白/备忘页（hitorigoto / memo / child.txt），一并看。

每个 URL 取全部快照时间戳，逐份抓 id_ 原始字节，抽出正文前若干字打到日志里，
同时落盘到 out_deep11/pages/ 供后续解析。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep11"
CDX = "http://web.archive.org/cdx/search/cdx"
UA = {"User-Agent": "Mozilla/5.0 (research; contact: none)"}

TARGETS = [
    "music.geocities.jp/withr17/diary.html",
    "www.geocities.jp/amorxxx79/diary.html",
    "www.geocities.jp/amorxxx79/hitorigoto.html",
    "www.geocities.jp/amorxxx79/memo.html",
    "music.geocities.jp/withr17/memo.html",
    "www.geocities.jp/withr79/bbs.html",
    "www.geocities.jp/withr79/bbs1.html",
]


def cdx(url, limit=200):
    p = {"url": url, "output": "json", "matchType": "exact",
         "fl": "timestamp,original,statuscode,mimetype,length,digest",
         "limit": str(limit), "collapse": "digest"}
    u = CDX + "?" + urllib.parse.urlencode(p)
    for _ in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90) as r:
                b = r.read()
            if not b.strip():
                return []
            d = json.loads(b)
            return d[1:] if d else []
        except Exception:
            time.sleep(5)
    return []


def grab(ts, url):
    u = "http://web.archive.org/web/%sid_/%s" % (ts, url)
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90) as r:
                return r.read()
        except Exception:
            time.sleep(4)
    return b""


def textify(b):
    import gzip
    if b[:2] == b"\x1f\x8b":
        try:
            b = gzip.decompress(b)
        except Exception:
            pass
    t = b.decode("cp932", "replace")
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "\n", t)
    t = re.sub(r"&nbsp;", " ", t)
    lines = [l.strip() for l in t.split("\n")]
    return "\n".join([l for l in lines if l])


def main():
    os.makedirs(OUT + "/pages", exist_ok=True)
    summary = []
    for url in TARGETS:
        rows = cdx(url)
        print("\n" + "=" * 70)
        print("URL", url, "快照", len(rows), "份")
        if rows:
            print("  时间跨度", rows[0][0][:8], "..", rows[-1][0][:8])
        got = 0
        for r in rows:
            ts = r[0]
            b = grab(ts, url)
            if len(b) < 300:
                continue
            name = "%s__%s.html" % (url.replace("/", "_").replace(":", ""), ts)
            open(os.path.join(OUT, "pages", name), "wb").write(b)
            got += 1
            txt = textify(b)
            print("  --- %s  %d bytes  正文 %d 字" % (ts, len(b), len(txt)))
            print("      " + txt[:260].replace("\n", " / "))
        summary.append({"url": url, "snapshots": len(rows), "saved": got,
                        "first": rows[0][0] if rows else None,
                        "last": rows[-1][0] if rows else None})
    json.dump(summary, open(OUT + "/summary.json", "w"), ensure_ascii=False, indent=1)
    print("\n完成", sum(s["saved"] for s in summary), "份页面")


if __name__ == "__main__":
    main()
