#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二十轮：进 withr79 别馆（以及更早的 ribbon.to 版本）翻全集。

线索链：
    2005-04 的 ONE's 首页写着
      「なお、別館「With R」は移転致しました。移転先は http://www.geocities.jp/withr79/」
    → amorxxx79 = ONE's 本馆（MIDI），withr79 = 别馆 With R（和 rico 合的那个）
    → 2010 年后别馆又搬到 music.geocities.jp/withr17/

如果 2005-2008 年的日记存在于网络上，最可能就在 withr79。这一站此前
只抓过 bbs.html / bbs1.html 两个 frameset，正文页一个没碰。

本轮：
  1. withr79 全量 CDX（不折叠），列出每个路径与份数。
  2. 把其中全部 HTML 抓下来，落盘。
  3. 每份抽 <a> 与 <frame>，找 diary / 日記 / 拍手 / bbs。
  4. 顺带把 2004-11 的 yellow.ribbon.to/~withr/ 也扫一遍（更早的地址）。
"""
import gzip
import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict

OUT = "out_deep20"
CDX = "http://web.archive.org/cdx/search/cdx"
UA = {"User-Agent": "Mozilla/5.0 (research)"}

PREFIXES = [
    "geocities.jp/withr79/",
    "yellow.ribbon.to/~withr/",
    "withr.y.ribbon.to/",
]


def log(*a):
    print(*a, flush=True)


def cdx(url, match="prefix", limit=5000):
    p = {"url": url, "output": "json", "matchType": match,
         "fl": "timestamp,original,statuscode,mimetype,length,digest",
         "limit": str(limit)}
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
            log("    重试 %d %s" % (i + 1, type(e).__name__))
            time.sleep(10)
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
            time.sleep(5)
    return b""


def text_of(b):
    if not b:
        return ""
    if b[:2] == b"\x1f\x8b":
        try:
            b = gzip.decompress(b)
        except Exception:
            pass
    for enc in ("cp932", "utf-8", "euc-jp"):
        try:
            return b.decode(enc)
        except Exception:
            continue
    return b.decode("cp932", "replace")


def links_of(t):
    out = []
    for m in re.finditer(r'<a[^>]+href\s*=\s*["\']?([^"\'\s>]+)[^>]*>(.*?)</a>',
                         t, re.S | re.I):
        out.append((re.sub(r"<[^>]+>", "", m.group(2)).strip()[:26], m.group(1)[:90]))
    for m in re.finditer(r'<frame[^>]+src\s*=\s*["\']?([^"\'\s>]+)', t, re.I):
        out.append(("[frame]", m.group(1)[:90]))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    allrep = {}

    for pre in PREFIXES:
        log("\n===== %s =====" % pre)
        rows = cdx(pre)
        log("  条目 %d" % len(rows))
        if not rows:
            continue
        json.dump(rows, open(os.path.join(
            OUT, re.sub(r"\W+", "_", pre) + ".json"), "w"))
        byp = defaultdict(list)
        for r in rows:
            byp[urllib.parse.urlparse(r[1]).path].append(r)
        log("  独立路径 %d" % len(byp))
        for k in sorted(byp):
            ts = sorted(x[0] for x in byp[k])
            log("    %-40s %2d 份  %s..%s" % (k[:40], len(ts), ts[0][:8], ts[-1][:8]))

        rep = {}
        for k, rs in sorted(byp.items()):
            if not k.lower().endswith((".html", ".htm")):
                continue
            # 取最新一份，另取最早一份，两相对比
            for tag, r in (("first", sorted(rs)[0]), ("last", sorted(rs)[-1])):
                b = grab(r[0], r[1])
                t = text_of(b)
                if not t:
                    continue
                fn = "%s_%s_%s.html" % (re.sub(r"\W+", "_", pre)[:16],
                                        r[0][:14], k.strip("/").replace("/", "_") or "root")
                open(os.path.join(OUT, fn), "w", encoding="utf-8").write(t)
                ls = links_of(t)
                own = [x for x in ls if not x[1].startswith("http")]
                log("    [%s %s] %-26s %5dB 链接%d（内部%d）" %
                    (tag, r[0][:14], k[-26:], len(t), len(ls), len(own)))
                for lb, hr in own:
                    log("         %-24s -> %s" % (lb, hr))
                rep.setdefault(k, []).append({"ts": r[0], "tag": tag,
                                              "len": len(t), "links": ls})
                time.sleep(1.2)
        allrep[pre] = rep

    json.dump(allrep, open(os.path.join(OUT, "links.json"), "w"),
              ensure_ascii=False, indent=1)
    log("\n完成")


if __name__ == "__main__":
    main()
