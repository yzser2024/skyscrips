#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓 yellow.ribbon.to/~withr/ 全站（PDF 清单第 XV 项），并探测 hpranking 域。"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_deep74"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research; withr-archive)"}


def get(url, tries=4, timeout=60):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                time.sleep(18 + i * 18)
                continue
            if e.code == 404:
                return None
        except Exception:
            time.sleep(8)
    return None


def cdx(prefix):
    q = ("http://web.archive.org/cdx/search/cdx?url=%s*&output=json"
         "&fl=original,timestamp,statuscode,length&collapse=urlkey"
         "&filter=statuscode:200&limit=3000" % urllib.parse.quote(prefix, safe=""))
    b = get(q, tries=4)
    if not b:
        return []
    try:
        return json.loads(b.decode("utf-8", "replace"))[1:]
    except Exception:
        return []


rows = cdx("yellow.ribbon.to/~withr/")
print("XV rows", len(rows), flush=True)
json.dump(rows, open(os.path.join(OUT, "cdx_yellow.json"), "w"), ensure_ascii=False, indent=1)
for r in rows[:80]:
    print(r, flush=True)

# 抓 html 页（最多 25 页）
n = 0
for original, ts, code, length in rows:
    if not re.search(r"\.html?$", original, re.I):
        continue
    if n >= 25:
        break
    url = "http://web.archive.org/web/%sid_/%s" % (ts, original)
    b = get(url)
    if b:
        fn = re.sub(r"[^0-9A-Za-z._-]", "_", original.split("//")[-1])[-80:] + "__" + ts + ".html"
        open(os.path.join(OUT, fn), "wb").write(b)
        print("ok", original, ts, len(b), flush=True)
        n += 1
    else:
        print("FAIL", original, ts, flush=True)
    time.sleep(1.2)

# hpranking 探测
for host in ["hpranking.cin", "hpranking.cin/cgi", "www.hpranking.cin"]:
    q = ("http://web.archive.org/cdx/search/cdx?url=%s*&output=json&fl=original,timestamp"
         "&collapse=urlkey&limit=20" % urllib.parse.quote(host, safe=""))
    b = get(q, tries=2)
    print("hpranking", host, (b[:200] if b else None), flush=True)

print("done")
