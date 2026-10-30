#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 withr17 / withr79 / amorxxx79 全站，找出所有「歌词藏在 title 属性里」的页面。

判定：解码后统计 <a title="..."> 中含假名的条数、是否出现「オンマウス」、onmouseover。
输出 out_deep70/summary.json + out_deep70/hits/
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_deep70"
HITS = os.path.join(OUT, "hits")
os.makedirs(HITS, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (research; withr-archive)"}
PREFIXES = [
    ("withr17", "music.geocities.jp/withr17/"),
    ("withr79", "www.geocities.jp/withr79/"),
    ("amorxxx79", "www.geocities.jp/amorxxx79/"),
]


def get(url, tries=4, timeout=60):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                time.sleep(20 + i * 20)
                continue
            if e.code == 404:
                return None
            time.sleep(8)
        except Exception:
            time.sleep(10)
    return None


def cdx(prefix):
    q = ("http://web.archive.org/cdx/search/cdx?url=%s*&output=json"
         "&fl=original,timestamp,statuscode&collapse=urlkey"
         "&filter=statuscode:200&limit=8000" % urllib.parse.quote(prefix, safe=""))
    b = get(q, tries=5)
    if not b:
        print("CDX FAIL", prefix)
        return []
    try:
        rows = json.loads(b.decode("utf-8", "replace"))
    except Exception:
        print("CDX BAD JSON", prefix, b[:200])
        return []
    return rows[1:] if rows else []


def decode(b):
    for enc in ("utf-8", "cp932", "euc-jp"):
        try:
            return b.decode(enc), enc
        except Exception:
            pass
    return b.decode("utf-8", "replace"), "utf-8/replace"


def analyse(html):
    ts = re.findall(r'<a[^>]*\btitle="([^"]*)"', html, re.I)
    jp = [t for t in ts if re.search(r"[ぁ-んァ-ヶ]", t)]
    alt = re.findall(r'\balt="([^"]*)"', html, re.I)
    altjp = [t for t in alt if re.search(r"[ぁ-んァ-ヶ]", t) and len(t) > 6]
    return {
        "a_title": len(ts),
        "a_title_jp": len(jp),
        "alt_jp": len(altjp),
        "onmouse": html.lower().count("onmouseover"),
        "onmouseword": html.count("オンマウス"),
        "sample": jp[:5],
    }


summary = {}
for name, prefix in PREFIXES:
    rows = cdx(prefix)
    print(name, "cdx rows", len(rows), flush=True)
    pages = [r for r in rows if re.search(r"\.html?$", r[0], re.I)]
    print(name, "html pages", len(pages), flush=True)
    got = []
    for original, ts, code in pages:
        key = original.split("//")[-1].split("?")[0]
        url = "http://web.archive.org/web/%sid_/%s" % (ts, original)
        b = get(url, tries=3, timeout=45)
        if not b:
            got.append({"url": original, "ts": ts, "err": "fetch"})
            continue
        html, enc = decode(b)
        a = analyse(html)
        a.update({"url": original, "ts": ts, "enc": enc, "bytes": len(b)})
        got.append(a)
        flag = a["a_title_jp"] >= 3 or a["onmouseword"] > 0
        if flag:
            fn = re.sub(r"[^0-9A-Za-z._-]", "_", key)[-90:] + "__" + ts + ".html"
            open(os.path.join(HITS, fn), "wb").write(b)
            print("HIT", original, ts, a["a_title_jp"], a["onmouseword"], flush=True)
        time.sleep(1.2)
    summary[name] = got

json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), ensure_ascii=False, indent=1)
print("done", {k: len(v) for k, v in summary.items()})
