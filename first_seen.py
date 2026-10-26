#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查歌词页在 Wayback 的首次存档时间（= 创作时间的可靠上界）。"""

import json
import time

import requests

CDX = "https://web.archive.org/cdx/search/cdx"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (compatible; personal-archive/1.0)"})

PAGES = [
    ("既遂", "oneyunn79.client.jp/kisui.html"),
    ("Specimen of butterflies", "oneyunn79.client.jp/cyou.html"),
    ("聖域に黴", "oneyunn79.client.jp/kabi.html"),
    ("贖罪", "oneyunn79.client.jp/syokuzai.html"),
    ("空に消えた君へ", "oneyunn79.client.jp/soranikietakimihe.html"),
    ("浅き夢との狭間にて", "oneyunn79.client.jp/asaki.html"),
    ("A left child", "oneyunn79.client.jp/child.html"),
    ("金魚の詩", "oneyunn79.client.jp/kingyo.html"),
    ("nature00", "oneyunn79.client.jp/nature00.html"),
    ("pumpkin magic", "oneyunn79.client.jp/pumpkin.html"),
    ("pp", "withr.y.ribbon.to/pp.html"),
    ("－ YOURS（对照）", "oneyunn79.client.jp/yours.html"),
    ("－ 千の炎（对照）", "oneyunn79.client.jp/honoo.html"),
    ("－ 歌词目录 kasi", "oneyunn79.client.jp/kasi.html"),
    ("－ 站点首页", "oneyunn79.client.jp/"),
]


def first_seen(url):
    try:
        r = S.get(CDX, params={
            "url": url, "output": "json",
            "fl": "timestamp,statuscode", "limit": "1",
        }, timeout=120)
        rows = r.json() if r.status_code == 200 and r.text.strip() else []
        if len(rows) < 2:
            return None, 0
        ts = rows[1][0]
        return ts, 1
    except Exception as e:
        return "ERR:" + repr(e)[:40], 0


def count(url):
    try:
        r = S.get(CDX, params={"url": url, "output": "json", "showNumPages": "true"}, timeout=60)
        return r.text.strip()[:20]
    except Exception:
        return "?"


out = []
for name, u in PAGES:
    ts, _ = first_seen(u)
    if ts and not ts.startswith("ERR"):
        t = "%s-%s-%s" % (ts[0:4], ts[4:6], ts[6:8])
    else:
        t = ts or "无记录"
    print("%-26s %-12s %s" % (name, t, u), flush=True)
    out.append({"name": name, "url": u, "first": t})
    time.sleep(0.6)

json.dump(out, open("first_seen.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n已写入 first_seen.json", flush=True)
