#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十五轮：从友站的链接页反查 yukari 站的旧地址。

背景：2004-12 ～ 2007-10 这段日记，直接按 amorxxx79 / withr17 / oneyunn 查
CDX 都是空的。但当年她的站是「相互リンク」圈子里的一员，友站的 links 页
会写「ONE's」「With R」「ゆん」并挂上地址。只要有一份 2005-2007 的 links
页留下来，就能拿到她当时的真实 URL（可能是旧式 geocities 编号地址，
按用户名查根本查不到）。

做法：
  1. 候选友站（从她 BBS 帖子里抽出来的真实域名）。
  2. 每个站查 2004-2007 的 HTML，挑出 link / banner / menu 类页面。
  3. 逐份抓原始字节，扫「oneyunn / withr / ゆん / ONE's / ユン」附近的 URL。
  4. 把命中的 (友站, 快照时间, 目标URL) 全列出来。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict

OUT = "out_deep15"
CDX = "http://web.archive.org/cdx/search/cdx"
UA = {"User-Agent": "Mozilla/5.0 (research)"}

HOSTS = [
    "a-colors.org",
    "free.meganebu.com",
    "chiaki-asuka.hiho.jp",
    "cabin.jp",
    "pop-mate.lovepop.jp",
    "fk.lovepop.jp",
    "yasuto.ddo.jp",
    "jump-ss.pupu.jp",
    "s2.poporo.net",
    "page.freett.com",
    "psyco.jp",
    "kannra.rdap.jp",
    "wing15.norify.jp",
    "yumesato.com",
    "pf-x.net",
    "x-axis.hippy.jp",
    "shirube.client.jp",
    "amaryllis.client.jp",
    "samuraiprincess.boy.jp",
    "sweety.jp",
]

# 她可能出现的字样
NEEDLES = ["oneyunn", "withr", "ONE's", "ＯＮＥ’ｓ", "ゆん", "ユン", "yunn"]

LINKISH = re.compile(r"(link|banner|menu|top|index|about|profile)", re.I)


def log(*a):
    print(*a, flush=True)


def cdx(url, match="domain", frm=None, to=None, limit=3000):
    p = {"url": url, "output": "json", "matchType": match,
         "fl": "timestamp,original,statuscode,mimetype,length",
         "limit": str(limit), "collapse": "urlkey"}
    if frm:
        p["from"] = frm
    if to:
        p["to"] = to
    u = CDX + "?" + urllib.parse.urlencode(p)
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA),
                                        timeout=150) as r:
                b = r.read()
            if not b.strip():
                return []
            d = json.loads(b)
            return d[1:] if d else []
        except Exception:
            time.sleep(6)
    return []


def grab(ts, url):
    u = "http://web.archive.org/web/%sid_/%s" % (ts, url)
    for i in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA),
                                        timeout=90) as r:
                return r.read()
        except Exception:
            time.sleep(3)
    return b""


def text_of(b):
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
    report = {}
    got = 0

    for host in HOSTS:
        log("\n===== %s =====" % host)
        rows = cdx(host, "domain", "2004", "2008", limit=4000)
        log("  2004-2007 条目 %d" % len(rows))
        if not rows:
            continue
        sel = [r for r in rows
               if r[3] and ("html" in r[3] or r[3] in ("text/html",))
               and LINKISH.search(urllib.parse.urlparse(r[1]).path or "/")]
        # 每个路径只留一份最早的
        byp = {}
        for r in sorted(sel):
            k = urllib.parse.urlparse(r[1]).path
            byp.setdefault(k, r)
        log("  链接类页面 %d" % len(byp))

        hits = []
        for k, r in list(byp.items())[:12]:
            b = grab(r[0], r[1])
            if not b:
                continue
            t = text_of(b)
            for nd in NEEDLES:
                if nd in t:
                    # 抽出附近的 URL
                    i = t.find(nd)
                    seg = t[max(0, i - 500):i + 500]
                    urls = re.findall(r"https?://[^\s\"'<>）\)]+", seg)
                    urls = [u for u in urls if "geocities" in u or "yf04" in u
                            or "client.jp" in u or "rocketbbs" in u]
                    hits.append({"host": host, "snapshot": r[0],
                                 "page": r[1], "needle": nd,
                                 "near_urls": urls[:8]})
                    log("  命中 %-10s %s %s" % (nd, r[0], r[1][:80]))
                    for u in urls[:8]:
                        log("      ->", u[:110])
                    break
            time.sleep(0.8)
        if hits:
            report[host] = hits
            got += len(hits)
        time.sleep(2)

    json.dump(report, open(os.path.join(OUT, "linkback.json"), "w"),
              ensure_ascii=False, indent=1)
    log("\n完成，命中 %d 条，涉及 %d 个友站" % (got, len(report)))


if __name__ == "__main__":
    main()
