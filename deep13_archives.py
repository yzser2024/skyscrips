#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十三轮：Wayback 之外的存档方普查。

目标：2004-12 ～ 2008-09 这段日记，Wayback 的 CDX 是空的。
换五个来源再问一次：

  1. WARP（日本国立国会图书馆 web 存档）—— 只收日本境内网站，geocities.jp
     2019 年关站时与 NDL 有官方合作，可能整站收过。
  2. Memento TimeTravel —— 聚合十几家存档（archive.today / Bibliotheca
     Alexandrina / LOC / archive-it / Icelandic / Portuguese ...），一次问全部。
  3. Archive Team 的 geocities-jp WARC 集合 —— 2019 年关站时民间整体抓取，
     存在 archive.org 的独立 item 里，不在 Wayback CDX 里。
  4. ウェブ魚拓（gyo.tc）—— 日本本土的网页鱼拓服务，2007 年起。
  5. Common Crawl —— 2013 年起，站点当时还活着。
  6. archive.today 直连（换个入口再试一次）。

全部结果落盘 + 打日志，不依赖成败。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep13"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Accept-Language": "ja,en;q=0.8"}

# 要找的东西：三处日记，加上站点根
TARGETS = [
    "http://www.geocities.jp/amorxxx79/diary.html",
    "http://www.geocities.jp/amorxxx79/",
    "http://music.geocities.jp/withr17/diary.html",
    "http://music.geocities.jp/withr17/",
    "http://www.geocities.jp/withr79/",
]


def get(url, timeout=60, retries=2):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            try:
                return e.code, e.read(), dict(e.headers or {})
            except Exception:
                return e.code, b"", {}
        except Exception as e:
            if i == retries - 1:
                return -1, str(e).encode()[:400], {}
            time.sleep(4)
    return -1, b"", {}


def save(name, data):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    with open(p, "wb") as f:
        f.write(data if isinstance(data, bytes) else str(data).encode())
    return p


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- 1. WARP
def probe_warp():
    log("\n===== 1. WARP (warp.ndl.go.jp) =====")
    # WARP 的检索是「サイト単位」的，先摸清表单参数
    forms = [
        "https://warp.ndl.go.jp/collections/search?keyword=amorxxx79",
        "https://warp.ndl.go.jp/collections/search?url=" +
        urllib.parse.quote("http://www.geocities.jp/amorxxx79/", safe=""),
        "https://warp.ndl.go.jp/collections/search?searchWord=amorxxx79",
        "https://warp.ndl.go.jp/collections/search?q=amorxxx79",
        "https://warp.ndl.go.jp/collections/",
    ]
    for i, u in enumerate(forms):
        st, b, h = get(u, 45)
        save("warp_%d.html" % i, b)
        n = len(b)
        txt = b.decode("utf-8", "replace")
        hit = ("amorxxx79" in txt) or ("withr" in txt)
        log("  [%d] %s -> %s %dB 命中关键词=%s" % (i, u[:78], st, n, hit))
        if hit:
            for m in re.finditer(r".{80}(?:amorxxx79|withr).{80}", txt):
                log("      ...", re.sub(r"<[^>]+>", " ", m.group(0))[:160])
        time.sleep(2)

    # WARP 的 URL 检索实际接口（ndljp pid 形式）
    for kw in ("amorxxx79", "withr17", "oneyunn"):
        u = ("https://warp.ndl.go.jp/collections/search?"
             "url=" + urllib.parse.quote("http://www.geocities.jp/" + kw + "/", safe=""))
        st, b, h = get(u, 45)
        log("  URL检索 %-10s -> %s %dB" % (kw, st, len(b)))
        time.sleep(2)


# ------------------------------------------------------- 2. Memento 聚合
def probe_memento():
    log("\n===== 2. Memento TimeTravel =====")
    for t in TARGETS:
        for kind in ("timemap/link", "api/json"):
            u = "http://timetravel.mementoweb.org/%s/%s" % (kind, t)
            st, b, h = get(u, 60)
            txt = b.decode("utf-8", "replace")
            save("memento_%s_%s.txt" % (kind.replace("/", "_"),
                                        re.sub(r"\W+", "_", t)[-40:]), b)
            links = re.findall(r'<(https?://[^>]+)>;\s*datetime="([^"]+)"', txt)
            log("  %-46s %-12s %s %dB  memento=%d" %
                (t[:46], kind, st, len(b), len(links)))
            for L, dt in links[:12]:
                log("      %s  %s" % (dt, L[:110]))
            time.sleep(2)


# ------------------------------------------- 3. Archive Team geocities-jp
def probe_archiveteam():
    log("\n===== 3. Archive Team geocities-jp @ archive.org =====")
    queries = [
        'collection:archiveteam AND geocities',
        'identifier:geocities*',
        'title:(geocities japan)',
        'geocities-jp',
        'geocitiesjp',
    ]
    for q in queries:
        u = ("https://archive.org/advancedsearch.php?q=" + urllib.parse.quote(q) +
             "&fl%5B%5D=identifier&fl%5B%5D=title&fl%5B%5D=item_size"
             "&fl%5B%5D=publicdate&rows=40&page=1&output=json")
        st, b, h = get(u, 60)
        try:
            d = json.loads(b)
            docs = d["response"]["docs"]
            num = d["response"]["numFound"]
        except Exception:
            docs, num = [], -1
        log("  q=%-42s %s numFound=%s" % (q, st, num))
        for it in docs[:12]:
            log("      %-34s %8.1f MB  %s" %
                (it.get("identifier", "")[:34],
                 (it.get("item_size") or 0) / 1048576, it.get("title", "")[:50]))
        time.sleep(2)

    # 直接探几个可能的 item 名
    for ident in ("geocities-jp", "geocitiesjp", "archiveteam_geocitiesjp",
                  "geocities-jp-2019", "geocities"):
        u = "https://archive.org/metadata/" + ident
        st, b, h = get(u, 45)
        try:
            d = json.loads(b)
            files = d.get("files", [])
            log("  metadata/%-28s %s files=%d" % (ident, st, len(files)))
            for f in files[:6]:
                log("      %-46s %s MB" % (f.get("name", "")[:46],
                                          round(int(f.get("size", 0)) / 1048576, 1)))
        except Exception:
            log("  metadata/%-28s %s (非 json)" % (ident, st))
        time.sleep(1)


# ------------------------------------------------------------ 4. ウェブ魚拓
def probe_gyotc():
    log("\n===== 4. ウェブ魚拓 (gyo.tc) =====")
    for t in TARGETS[:3]:
        for u in ("http://gyo.tc/?url=" + urllib.parse.quote(t, safe=""),
                  "http://gyo.tc/" + t):
            st, b, h = get(u, 40, retries=1)
            txt = b.decode("utf-8", "replace")
            log("  %-70s %s %dB" % (u[:70], st, len(b)))
            if "魚拓" in txt or "gyo.tc" in txt:
                m = re.search(r"(\d{4}/\d{2}/\d{2}[^<]{0,30})", txt)
                if m:
                    log("      日期线索:", m.group(1))
            time.sleep(1)


# ------------------------------------------------------- 5. Common Crawl
def probe_commoncrawl():
    log("\n===== 5. Common Crawl index =====")
    cols = ["CC-MAIN-2019-13", "CC-MAIN-2018-39", "CC-MAIN-2017-43",
            "CC-MAIN-2016-44", "CC-MAIN-2015-35", "CC-MAIN-2014-41"]
    for col in cols:
        for t in ("geocities.jp/amorxxx79/*", "music.geocities.jp/withr17/*"):
            u = ("https://index.commoncrawl.org/%s-index?url=%s&output=json" %
                 (col, urllib.parse.quote(t, safe="")))
            st, b, h = get(u, 45, retries=1)
            n = b.count(b"\n")
            log("  %-16s %-34s %s 行=%d" % (col, t, st, n))
            if st == 200 and n:
                save("cc_%s_%s.jsonl" % (col, t.split("/")[0].replace(".", "_")), b)
                for line in b.decode("utf-8", "replace").splitlines()[:4]:
                    log("      ", line[:150])
            time.sleep(1)


# --------------------------------------------------------- 6. archive.today
def probe_archivetoday():
    log("\n===== 6. archive.today =====")
    hosts = ["https://archive.ph", "https://archive.is", "https://archive.today"]
    for h in hosts:
        st, b, hd = get(h + "/", 30, retries=1)
        log("  %-24s 首页 %s %dB" % (h, st, len(b)))
    for t in TARGETS[:2]:
        for h in ("https://archive.ph", "https://archive.is"):
            st, b, hd = get(h + "/newest/" + t, 40, retries=1)
            log("  %-24s newest %-46s %s %dB" % (h, t[-46:], st, len(b)))


def main():
    os.makedirs(OUT, exist_ok=True)
    log("目标：", len(TARGETS), "个 URL × 6 家存档")
    for fn in (probe_warp, probe_memento, probe_archiveteam,
               probe_gyotc, probe_commoncrawl, probe_archivetoday):
        try:
            fn()
        except Exception as e:
            log("  !! %s 异常 %s: %s" % (fn.__name__, type(e).__name__, e))
    log("\n完成。产物在", OUT)


if __name__ == "__main__":
    main()
