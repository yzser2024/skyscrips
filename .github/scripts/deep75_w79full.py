#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""withr79 全量快照抓取：把 2005-2007 的每个时间点都取回来，并核查音频/图片是否有存档。"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_deep75"
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
                time.sleep(15 + i * 15)
                continue
            if e.code == 404:
                return None
        except Exception:
            time.sleep(6)
    return None


def cdx(q):
    b = get(q, tries=4)
    if not b:
        return []
    try:
        d = json.loads(b.decode("utf-8", "replace"))
        return d[1:] if d else []
    except Exception:
        return []


# 1) 全量快照（不 collapse），看每个版本
q_all = ("http://web.archive.org/cdx/search/cdx?url=www.geocities.jp/withr79/*"
         "&output=json&fl=original,timestamp,statuscode,length"
         "&filter=statuscode:200&limit=4000")
rows = cdx(q_all)
print("ALL rows", len(rows), flush=True)
json.dump(rows, open(os.path.join(OUT, "cdx_all.json"), "w"), ensure_ascii=False, indent=1)

ext = {}
for orig, ts, code, length in rows:
    m = re.search(r"\.([A-Za-z0-9]{2,4})$", orig)
    e = m.group(1).lower() if m else "none"
    ext.setdefault(e, []).append((orig, ts, length))
for e in sorted(ext, key=lambda k: -len(ext[k])):
    print("EXT", e, len(ext[e]), flush=True)
    for x in ext[e][:12]:
        print("   ", x, flush=True)

# 2) 抓全部 html 快照（按时间戳去重，最多 80 个）
seen = set()
n = 0
for orig, ts, code, length in rows:
    if not re.search(r"\.html?$", orig, re.I):
        continue
    key = (orig, ts)
    if key in seen or n >= 80:
        continue
    seen.add(key)
    url = "http://web.archive.org/web/%sid_/%s" % (ts, orig)
    b = get(url)
    if b:
        name = orig.split("withr79/")[-1].replace("/", "_") or "index.html"
        fn = "%s__%s.html" % (name.rsplit(".", 1)[0], ts)
        open(os.path.join(OUT, fn), "wb").write(b)
        print("ok", orig, ts, len(b), flush=True)
        n += 1
    else:
        print("FAIL", orig, ts, flush=True)
    time.sleep(1.0)

# 3) 音频/图片单独查（不限 withr79 前缀，看是否换过路径）
for pat in ["www.geocities.jp/withr79/*.mp3", "www.geocities.jp/withr79/*.jpg",
            "www.geocities.jp/withr79/*.gif", "www.geocities.jp/withr79/*.png"]:
    q = ("http://web.archive.org/cdx/search/cdx?url=%s&output=json"
         "&fl=original,timestamp,statuscode,length&collapse=urlkey&limit=200"
         % urllib.parse.quote(pat, safe=""))
    r = cdx(q)
    print("PROBE", pat, len(r), flush=True)
    for x in r[:20]:
        print("   ", x, flush=True)

print("done")
