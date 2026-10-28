#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第八轮：换存档商。Wayback 对 oneday 板只存了 3 页（p1/p2/p5），
2009 年那一段在 CDX 里根本不存在。archive.today 是另一套独立抓取，
时间点和 Wayback 不同，先查 timemap 看有没有补齐的可能。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep8"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"}

TARGETS = [
    "http://www5.rocketbbs.com/651/bbs.cgi?id=oneday&page=3",
    "http://www5.rocketbbs.com/651/bbs.cgi?id=oneday&page=4",
    "http://www5.rocketbbs.com/651/oneday.html",
    "http://www5.rocketbbs.com/651/bbs.cgi?id=withr",
    "http://music.geocities.jp/withr17/diary/",
    "http://music.geocities.jp/withr17/",
]

HOSTS = ["archive.ph", "archive.today", "archive.is", "archive.li", "archive.md"]


def get(url, timeout=45):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                    timeout=timeout) as r:
            return r.read()
    except Exception as e:
        return b""


def main():
    os.makedirs(OUT, exist_ok=True)
    log = []
    host = None
    for h in HOSTS:
        b = get("https://%s/" % h, timeout=25)
        if b:
            host = h
            print("可用主机", h, len(b))
            break
    if not host:
        print("archive.today 全域名不可达")
        return

    for t in TARGETS:
        tm = "https://%s/timemap/%s" % (host, t)
        b = get(tm, timeout=40)
        print("==", t)
        print("   timemap", len(b))
        if b:
            open(os.path.join(OUT, re.sub(r"[^A-Za-z0-9]", "_", t)[:70] + ".timemap"),
                 "wb").write(b)
            txt = b.decode("utf-8", "replace")
            ts = re.findall(r"/(\d{14})/", txt)
            print("   时间点", len(ts), ts[:12])
        # newest 页
        b2 = get("https://%s/newest/%s" % (host, t), timeout=40)
        print("   newest", len(b2))
        if b2 and len(b2) > 2000:
            p = os.path.join(OUT, re.sub(r"[^A-Za-z0-9]", "_", t)[:70] + ".html")
            open(p, "wb").write(b2)
        time.sleep(3)

    json.dump({"host": host}, open(os.path.join(OUT, "meta.json"), "w"))


if __name__ == "__main__":
    main()
