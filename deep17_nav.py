#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十七轮：六个时间点的首页/导航页，看「日記」这一项指向哪里。

思路：diary.html 本身只有 2008 年两份，但站点的首页和导航页在 2005-2018
之间有十几个快照。这些页面的菜单里一定有一项写着「日記」或「diary」，
它的 href 就是当时的真实地址。逐期对比，就能还原：
    2005 年日记在哪 → 2007 年搬到哪 → 2008 年换到哪个板 → 2018 年还在不在

同时把这些页的「更新履歴 / BBS / 拍手」链接一起抽出来，
作为后续可查的目标。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep17"
UA = {"User-Agent": "Mozilla/5.0 (research)"}

TARGETS = [
    ("20050416011713", "http://www.geocities.jp/amorxxx79/index.html"),
    ("20050803001740", "http://www.geocities.jp/amorxxx79/index.html"),
    ("20060107043326", "http://www.geocities.jp/amorxxx79/index.html"),
    ("20060614100857", "http://www.geocities.jp/amorxxx79/index.html"),
    ("20070505113930", "http://www.geocities.jp/amorxxx79/index.html"),
    ("20070810044345", "http://www.geocities.jp/amorxxx79/index.html"),
    ("20071027074127", "http://www.geocities.jp/amorxxx79/index.html"),
    ("20090131185854", "http://www.geocities.jp/amorxxx79/index.html"),
    ("20090927205957", "http://www.geocities.jp/amorxxx79/index.html"),
    ("20181105203824", "http://www.geocities.jp/amorxxx79/index.html"),
    ("20070209102406", "http://www.geocities.jp/amorxxx79/top.html"),
    ("20071016221411", "http://www.geocities.jp/amorxxx79/top.html"),
    ("20080215111751", "http://www.geocities.jp/amorxxx79/top.html"),
    ("20080416152918", "http://www.geocities.jp/amorxxx79/top.html"),
    ("20080512160716", "http://www.geocities.jp/amorxxx79/top.html"),
    ("20081222135850", "http://www.geocities.jp/amorxxx79/top.html"),
    ("20101211075804", "http://www.geocities.jp/amorxxx79/top.html"),
    ("20090813031616", "http://www.geocities.jp/amorxxx79/mylink.html"),
    ("20060111053419", "http://www.geocities.jp/amorxxx79/menu.html"),
    ("20070915000000", "http://www.geocities.jp/amorxxx79/midimenu.html"),
]

DIARY_WORDS = ("日記", "diary", "Diary", "ダイアリー", "拍手", "更新")


def log(*a):
    print(*a, flush=True)


def grab(ts, url):
    u = "http://web.archive.org/web/%sid_/%s" % (ts, url)
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA),
                                        timeout=90) as r:
                return r.read()
        except Exception:
            time.sleep(5)
    return b""


def text_of(b):
    if not b:
        return ""
    if b[:2] == b"\x1f\x8b":
        try:
            import gzip
            b = gzip.decompress(b)
        except Exception:
            pass
    for enc in ("cp932", "utf-8", "euc-jp"):
        try:
            return b.decode(enc)
        except Exception:
            continue
    return b.decode("cp932", "replace")


def main():
    os.makedirs(OUT, exist_ok=True)
    report = []
    for ts, url in TARGETS:
        b = grab(ts, url)
        t = text_of(b)
        if not t:
            log("%s  %-52s 取空" % (ts, url))
            continue
        name = "%s_%s" % (ts, url.rstrip("/").split("/")[-1])
        open(os.path.join(OUT, name + ".html"), "w", encoding="utf-8").write(t)

        links = []
        for m in re.finditer(r'<a[^>]+href\s*=\s*["\']?([^"\'\s>]+)["\']?[^>]*>(.*?)</a>',
                             t, re.S | re.I):
            href = m.group(1)
            label = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            links.append((label[:24], href[:90]))
        diary = [l for l in links if any(w in l[0] for w in DIARY_WORDS)]
        log("\n%s  %s  %dB  链接%d" % (ts, url.split("/")[-1], len(t), len(links)))
        if diary:
            for lb, hr in diary:
                log("    ★ %-22s -> %s" % (lb, hr))
        else:
            log("    （本页无 diary/更新类链接）")
            for lb, hr in links[:10]:
                log("      %-22s -> %s" % (lb, hr))
        report.append({"ts": ts, "url": url, "links": links, "diary": diary})
        time.sleep(2)

    json.dump(report, open(os.path.join(OUT, "nav.json"), "w"),
              ensure_ascii=False, indent=1)
    log("\n完成 %d 页" % len(report))


if __name__ == "__main__":
    main()
