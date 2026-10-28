#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十六轮：找 Archive Team 的 Geocities Japan 单站 WARC。

上一轮发现 archive.org 上有一批 item 命名形如：
    warc_www_geocities_jp-tuguhana      title: WARC: www.geocities.jp/tuguhana/
    warc-www_geocities_jp-f_tamakoku    title: WARC: www.geocities.jp/f_tamakoku/
说明 Archive Team 在 2018-11 日本 geocities 关站前，把站点**一站一个 WARC**
抓了下来，而且 title 字段直接写着完整 URL。

如果 amorxxx79 在里面，2018 年的最终版 diary.html 就有机会拿到——那会是
比她 2009 年更完整的版本（她 2008-09 换成日记板后，静态 diary.html 是否
继续维护、有没有把旧条目留在页面里，都能从这份最终版看出来）。

做法：
  1. 按 title / identifier / 全文多个角度搜 amorxxx79、withr17、withr79、oneyunn。
  2. 把 identifier 以 warc 开头的 geocities 相关 item 全部列出来（最多几百条），
     本地筛 amorxxx。
  3. 命中的 item 取 metadata，列文件，挑最小的 warc 下载并解析。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep16"
UA = {"User-Agent": "Mozilla/5.0 (research)"}
KEYS = ["amorxxx79", "withr17", "withr79", "oneyunn", "yukari"]


def log(*a):
    print(*a, flush=True)


def get(url, timeout=90, retries=3):
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b""
        except Exception:
            time.sleep(6)
    return -1, b""


def adv(q, rows=100):
    u = ("https://archive.org/advancedsearch.php?q=" + urllib.parse.quote(q) +
         "&fl%5B%5D=identifier&fl%5B%5D=title&fl%5B%5D=item_size"
         "&fl%5B%5D=publicdate&rows=%d&page=1&output=json" % rows)
    st, b = get(u)
    try:
        d = json.loads(b)
        return d["response"]["numFound"], d["response"]["docs"]
    except Exception:
        return -1, []


def main():
    os.makedirs(OUT, exist_ok=True)
    found = {}

    log("===== 1. 按关键词搜 title / identifier / 全文 =====")
    queries = []
    for k in KEYS:
        queries += ['title:(%s)' % k, 'identifier:(%s)' % k, k]
    queries += ['identifier:warc*geocities*',
                'title:("geocities.jp/amorxxx79")',
                'collection:archiveteam AND amorxxx79']
    for q in queries:
        num, docs = adv(q, 60)
        log("  q=%-40s numFound=%s" % (q, num))
        for it in docs[:10]:
            log("      %-42s %8.1f MB  %s" %
                (it.get("identifier", "")[:42],
                 (it.get("item_size") or 0) / 1048576,
                 it.get("title", "")[:52]))
            found.setdefault(it.get("identifier"), it)
        time.sleep(1.5)

    log("\n===== 2. 列出全部 warc-*geocities* item =====")
    num, docs = adv('identifier:warc*geocities*', 2000)
    log("  numFound=%s" % num)
    names = sorted(d.get("identifier", "") for d in docs)
    for d in docs:
        found.setdefault(d.get("identifier"), d)
    json.dump(docs, open(os.path.join(OUT, "warc_geocities.json"), "w"),
              ensure_ascii=False)
    hits = [n for n in names if re.search(r"amor|withr|oneyunn|yunn", n, re.I)]
    log("  命中她站关键词的 item：%d" % len(hits))
    for n in hits:
        log("      ", n)

    log("\n===== 3. 命中 item 的文件清单 =====")
    for ident in hits:
        st, b = get("https://archive.org/metadata/" + ident)
        try:
            d = json.loads(b)
        except Exception:
            log("  %s metadata %s 解析失败" % (ident, st))
            continue
        files = d.get("files", [])
        log("  %s  文件 %d 个" % (ident, len(files)))
        for f in files:
            sz = int(f.get("size", 0) or 0)
            log("      %-58s %8.1f MB  %s" %
                (f.get("name", "")[:58], sz / 1048576, f.get("format", "")))
        json.dump(d, open(os.path.join(OUT, "meta_%s.json" % ident), "w"),
                  ensure_ascii=False)

    log("\n===== 4. 汇总 =====")
    log("  共见到 %d 个候选 item，命名命中 %d 个" % (len(found), len(hits)))
    json.dump(sorted(found), open(os.path.join(OUT, "seen_items.json"), "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
