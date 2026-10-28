#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二十四轮：oneday 日记板 —— 绕开分页，找「一次性全显示」的 URL。

情况：oneday 板共 200 条、6 页。p01 / p02 / p05 / p06 都有快照，
偏偏 p03 / p04（2009 年那一年）没有任何存档，`?id=oneday&page=3` 查不到。

但 rocketbbs 除分页外还支持一括表示 / 树形表示。若当年有人用那种 URL
抓过，200 条会在同一页里，p03/p04 的缺口就自然绕过去了。

本轮试：
  1. 651/oneday.html 本体与 651/bbs.cgi 的各参数组合（all / mode / n / tree / 全件表示）。
  2. 对 `bbs.cgi?id=oneday` 做前缀查（不折叠），把历史上出现过的所有
     参数形态列出来——包括从来没试过的。
  3. 命中就把整页抓下来，数条目、看日期范围。
"""
import gzip
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep24"
CDX = "http://web.archive.org/cdx/search/cdx"
UA = {"User-Agent": "Mozilla/5.0 (research)"}
HOSTS = ["www5.rocketbbs.com", "www1.rocketbbs.com", "www7.rocketbbs.com"]


def log(*a):
    print(*a, flush=True)


def cdx(url, match="prefix", limit=3000):
    p = {"url": url, "output": "json", "matchType": match,
         "fl": "timestamp,original,statuscode,mimetype,length",
         "limit": str(limit)}
    u = CDX + "?" + urllib.parse.urlencode(p)
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA),
                                        timeout=150) as r:
                b = r.read()
            if not b.strip():
                return []
            d = json.loads(b)
            return d[1:] if d else []
        except Exception as e:
            log("    重试 %d %s" % (i + 1, type(e).__name__))
            time.sleep(8)
    return []


def grab(ts, url):
    for i in range(3):
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(
                        "http://web.archive.org/web/%sid_/%s" % (ts, url),
                        headers=UA), timeout=90) as r:
                return r.read()
        except Exception:
            time.sleep(4)
    return b""


def text_of(b):
    if not b:
        return ""
    if b[:2] == b"\x1f\x8b":
        try:
            b = gzip.decompress(b)
        except Exception:
            pass
    return b.decode("cp932", "replace")


def main():
    os.makedirs(OUT, exist_ok=True)

    log("===== 1. 历史出现过的全部参数形态 =====")
    seen = {}
    for h in HOSTS:
        rows = cdx("%s/651/bbs.cgi" % h, "prefix")
        log("  %-22s %d 条" % (h, len(rows)))
        for r in rows:
            q = urllib.parse.urlparse(r[1]).query
            if "oneday" in r[1]:
                seen.setdefault(r[1], []).append(r[0])
    log("  含 oneday 的 URL 形态 %d 种" % len(seen))
    for u, ts in sorted(seen.items()):
        log("    %-56s %2d 份  %s..%s" % (u[-56:], len(ts), min(ts)[:8], max(ts)[:8]))

    log("\n===== 2. 一括表示类参数逐个试 =====")
    forms = [
        "/651/bbs.cgi?id=oneday&all=1",
        "/651/bbs.cgi?id=oneday&mode=all",
        "/651/bbs.cgi?id=oneday&n=200",
        "/651/bbs.cgi?id=oneday&page=1&n=200",
        "/651/bbs.cgi?id=oneday&tree=1",
        "/651/bbs.cgi?id=oneday&mode=tree",
        "/651/bbs.cgi?id=oneday&page=3",
        "/651/bbs.cgi?id=oneday&page=4",
        "/651/oneday.html",
    ]
    found = []
    for h in HOSTS:
        for f in forms:
            u = "http://%s%s" % (h, f)
            rows = cdx(u, "exact")
            if rows:
                ts = sorted(r[0] for r in rows)
                log("  %-72s %d 份  %s..%s" % (f, len(rows), ts[0][:8], ts[-1][:8]))
                found.append((h, f, rows))
            time.sleep(0.8)

    log("\n===== 3. 有快照的抓下来数条目 =====")
    for h, f, rows in found:
        for r in sorted(rows)[:2]:
            url = "http://%s%s" % (h, f)
            b = grab(r[0], url)
            t = text_of(b)
            if not t:
                continue
            dates = re.findall(r"\d{4}/\d{2}/\d{2}", t)
            cnt = re.search(r"(\d+)\s*/\s*(\d+)\s*件", t)
            fn = "%s_%s_%s.html" % (h.replace(".", "_"), r[0][:14],
                                    re.sub(r"\W+", "_", f)[-24:])
            open(os.path.join(OUT, fn), "w", encoding="utf-8").write(t)
            log("  %-56s %6dB 日期%d 计数%s" %
                (fn[-56:], len(t), len(dates), cnt.groups() if cnt else None))
            if dates:
                log("      范围 %s .. %s" % (min(dates), max(dates)))
            time.sleep(1.5)

    log("\n完成，命中形态 %d 组" % len(found))


if __name__ == "__main__":
    main()
