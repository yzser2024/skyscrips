#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WithR / ONE's 全站 CDX 普查：把已知域名下所有存档 URL 列出来，
重点看 rico 相关路径、日记的其他时间段、以及 PDF 清单里没记录过的页面。
只读 CDX，不抓正文，速度快、条目全。
"""
import json
import os
import time
import urllib.parse
import urllib.request

OUT = "out_deep"
CDX = "http://web.archive.org/cdx/search/cdx"

# (标签, CDX 查询串)
TARGETS = [
    ("withr-ribbon", "withr.y.ribbon.to/*"),
    ("yellow-withr", "yellow.ribbon.to/~withr/*"),
    ("music-geo-withr17", "music.geocities.jp/withr17/*"),
    ("geo-withr79", "www.geocities.jp/withr79/*"),
    ("geo-amorxxx79", "www.geocities.jp/amorxxx79/*"),
    ("rb610", "www1.rocketbbs.com/610/*"),
    ("rb651", "www5.rocketbbs.com/651/*"),
    ("rb310", "www1.rocketbbs.com/310/*"),
    ("jbbs-yf04", "yf04.com/cgi-bin/jbbs/*"),
    ("fc2-diary", "diary1.fc2.com/user/oneyunn79/*"),
    ("fc2-ed", "diary1.fc2.com/cgi-sys/ed.cgi/oneyunn79/*"),
    ("ones-client", "oneyunn79.client.jp/*"),
    ("yf04", "yf04.com/*"),
    ("hpranking", "www.hpranking.com/in.cgi*"),
    ("webclap", "clap.webclap.com/clap.php*oneyunn*"),
]


def cdx(q, limit=4000):
    params = {"url": q, "output": "json",
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
            print("  retry", i, type(e).__name__, q, flush=True)
            time.sleep(10)
    return []


def main():
    os.makedirs(OUT, exist_ok=True)
    summary = []
    for tag, q in TARGETS:
        print("== %s  %s" % (tag, q), flush=True)
        rows = cdx(q)
        print("   条目", len(rows), flush=True)
        json.dump(rows, open(os.path.join(OUT, tag + ".json"), "w"),
                  ensure_ascii=False, indent=0)
        html = [r for r in rows if r[4] and "html" in r[4]]
        summary.append({"tag": tag, "query": q, "rows": len(rows), "html": len(html)})
        # 单独把可疑的挑出来
        for r in rows:
            u = r[1]
            lu = u.lower()
            if any(k in lu for k in ("rico", "diary", "nikki", "log", "blog",
                                     "bbs", "essa", "column")):
                print("   *", r[0], r[2], u, flush=True)
    json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"),
              ensure_ascii=False, indent=1)
    print("=== 汇总 ===")
    for s in summary:
        print("%-18s rows=%-6d html=%-6d %s" % (s["tag"], s["rows"], s["html"], s["query"]))


if __name__ == "__main__":
    main()
