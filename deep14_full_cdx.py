#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十四轮：不折叠的完整 CDX。

之前的普查用了 collapse=urlkey，306 个路径每路径只剩 1 条。
于是「diary.html 只有 2 份快照」这个结论可能是折叠造成的假象。

这一轮改成：
  1. 对 amorxxx79 整个前缀做 collapse= 空的查询，把每条时间戳都拿回来，
     按路径汇总，看每个页面到底有多少份、时间跨度多宽。
  2. 单点查 diary.html / index.html / top.html / menu.html /
     hitorigoto.html / child.html / child.txt / mylink.html 的全量。
  3. 对 withr17 同样做一遍（它也可能是折叠假象）。
  4. 把「只在某年出现过的路径」单独列出来——那些往往是改版前的旧页面，
     里面可能就有早年的日记。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict

OUT = "out_deep14"
CDX = "http://web.archive.org/cdx/search/cdx"
UA = {"User-Agent": "Mozilla/5.0 (research)"}

PREFIXES = [
    "geocities.jp/amorxxx79/",
    "music.geocities.jp/withr17/",
    "geocities.jp/withr79/",
]

POINTS = [
    "geocities.jp/amorxxx79/diary.html",
    "geocities.jp/amorxxx79/index.html",
    "geocities.jp/amorxxx79/top.html",
    "geocities.jp/amorxxx79/menu.html",
    "geocities.jp/amorxxx79/hitorigoto.html",
    "geocities.jp/amorxxx79/child.html",
    "geocities.jp/amorxxx79/child.txt",
    "geocities.jp/amorxxx79/mylink.html",
    "music.geocities.jp/withr17/diary.html",
]


def log(*a):
    print(*a, flush=True)


def cdx(url, match="prefix", collapse=None, limit=20000):
    p = {"url": url, "output": "json", "matchType": match,
         "fl": "timestamp,original,statuscode,mimetype,length,digest",
         "limit": str(limit)}
    if collapse:
        p["collapse"] = collapse
    u = CDX + "?" + urllib.parse.urlencode(p)
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA),
                                        timeout=180) as r:
                b = r.read()
            if not b.strip():
                return []
            d = json.loads(b)
            return d[1:] if d else []
        except Exception as e:
            log("    重试 %d: %s" % (i + 1, type(e).__name__))
            time.sleep(8)
    return []


def main():
    os.makedirs(OUT, exist_ok=True)
    summary = {}

    for pre in PREFIXES:
        log("\n===== 全量前缀 %s =====" % pre)
        rows = cdx(pre, "prefix", None)
        log("  条目总数 %d" % len(rows))
        if not rows:
            continue
        json.dump(rows, open(os.path.join(
            OUT, re.sub(r"\W+", "_", pre) + "all.json"), "w"))
        bypath = defaultdict(list)
        for r in rows:
            u = urllib.parse.urlparse(r[1])
            bypath[u.path].append((r[0][:14], r[2], r[4]))
        log("  独立路径 %d" % len(bypath))
        # 多份的路径优先打
        multi = sorted(bypath.items(), key=lambda kv: -len(kv[1]))
        log("  —— 快照最多的 25 个路径 ——")
        for k, v in multi[:25]:
            ts = sorted(x[0] for x in v)
            log("    %-44s %3d 份  %s..%s" % (k[:44], len(v), ts[0][:8], ts[-1][:8]))
        summary[pre] = {k: len(v) for k, v in bypath.items()}
        time.sleep(3)

    log("\n===== 单点全量 =====")
    for u in POINTS:
        rows = cdx(u, "exact", None, limit=2000)
        ts = [r[0] for r in rows]
        digests = len(set(r[5] for r in rows)) if rows else 0
        log("  %-46s %3d 份  不同版本 %d" % (u[-46:], len(rows), digests))
        if ts:
            years = defaultdict(int)
            for t in ts:
                years[t[:4]] += 1
            log("      按年 " + " ".join("%s:%d" % (y, n) for y, n in sorted(years.items())))
            log("      " + ", ".join(ts[:20]))
        json.dump(rows, open(os.path.join(
            OUT, "pt_" + re.sub(r"\W+", "_", u) + ".json"), "w"))
        time.sleep(2)

    json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"),
              ensure_ascii=False)
    log("\n完成")


if __name__ == "__main__":
    main()
