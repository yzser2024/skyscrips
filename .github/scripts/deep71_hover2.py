#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精简版：只扫 withr17 / withr79；每个 URL 取最早快照，若快照晚于 2014 再补一个 2009-2012 的。
判定「歌词藏 title」：<a title> 中日文条数 >=3，或出现「オンマウス」。
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

OUT = "out_deep71"
HITS = os.path.join(OUT, "hits")
os.makedirs(HITS, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research; withr-archive)"}
PREFIXES = [("withr17", "music.geocities.jp/withr17/"),
            ("withr79", "www.geocities.jp/withr79/")]


def get(url, tries=3, timeout=45):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                time.sleep(10 + i * 15)
                continue
            if e.code == 404:
                return None
        except Exception:
            time.sleep(6)
    return None


def cdx(prefix, extra=""):
    q = ("http://web.archive.org/cdx/search/cdx?url=%s*&output=json"
         "&fl=original,timestamp&collapse=urlkey&filter=statuscode:200&limit=4000%s"
         % (urllib.parse.quote(prefix, safe=""), extra))
    b = get(q, tries=4)
    if not b:
        return []
    try:
        return json.loads(b.decode("utf-8", "replace"))[1:]
    except Exception:
        return []


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
    return {"a_title": len(ts), "a_title_jp": len(jp),
            "onmouseword": html.count("オンマウス"),
            "onmouseover": html.lower().count("onmouseover"),
            "sample": jp[:6]}


def fetch_one(job):
    original, ts = job
    url = "http://web.archive.org/web/%sid_/%s" % (ts, original)
    b = get(url)
    if not b:
        return {"url": original, "ts": ts, "err": "fetch"}
    html, enc = decode(b)
    a = analyse(html)
    a.update({"url": original, "ts": ts, "enc": enc, "bytes": len(b)})
    if a["a_title_jp"] >= 3 or a["onmouseword"] > 0:
        fn = re.sub(r"[^0-9A-Za-z._-]", "_", original.split("//")[-1])[-80:] + "__" + ts + ".html"
        open(os.path.join(HITS, fn), "wb").write(b)
        print("HIT", original, ts, a["a_title_jp"], a["onmouseword"], flush=True)
    return a


summary = {}
for name, prefix in PREFIXES:
    rows = [r for r in cdx(prefix) if re.search(r"\.html?$", r[0], re.I)]
    jobs = [(r[0], r[1]) for r in rows]
    # 补 2009-2012 快照（collapse=timestamp:6 按月）
    old = []
    for r in cdx(prefix, "&from=2005&to=2012&collapse=timestamp:6"):
        if re.search(r"\.html?$", r[0], re.I):
            old.append((r[0], r[1]))
    seen = {j[0] for j in jobs}
    extra = [j for j in old if j[0] in seen and j[1] < "20140101"]
    alljobs = jobs + extra
    print(name, "pages", len(jobs), "extra-old", len(extra), flush=True)
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(fetch_one, alljobs))
    summary[name] = res

json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), ensure_ascii=False, indent=1)
print("done", {k: len(v) for k, v in summary.items()})
