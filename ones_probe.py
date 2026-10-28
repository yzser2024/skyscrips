#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探测 ONE's 的日记（FC2）与 BBS（rocketbbs / jbbs）在 Wayback 里的快照清单。"""
import json
import os
import time

import requests

CDX = "https://web.archive.org/cdx/search/cdx"
OUT = "out"
os.makedirs(OUT, exist_ok=True)

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (personal-archive/1.0)"})

TARGETS = [
    # (标签, cdx url 参数, matchType)
    ("rocket310_www1", "www1.rocketbbs.com/310/", "prefix"),
    ("rocket310_www2", "www2.rocketbbs.com/310/", "prefix"),
    ("rocket310_www5", "www5.rocketbbs.com/310/", "prefix"),
    ("rocket310_bare", "rocketbbs.com/310/", "prefix"),
    ("rocket_root_oneyunn", "rocketbbs.com/310/oneyunn", "prefix"),
    ("jbbs_yf04", "yf04.com/cgi-bin/jbbs/", "prefix"),
    ("fc2_ed1", "diary1.fc2.com/cgi-sys/ed.cgi/oneyunn79", "prefix"),
    ("fc2_ed", "diary.fc2.com/cgi-sys/ed.cgi/oneyunn79", "prefix"),
    ("fc2_blog", "oneyunn79.blog.fc2.com", "prefix"),
    ("ones_site", "oneyunn79.client.jp", "prefix"),
]


def cdx(url, match, tries=3):
    for i in range(tries):
        try:
            r = S.get(CDX, params={
                "url": url,
                "matchType": match,
                "output": "json",
                "fl": "timestamp,original,statuscode,mimetype,length",
                "limit": "8000",
            }, timeout=240)
            if r.status_code != 200:
                print("  CDX %s -> %s" % (url, r.status_code), flush=True)
                time.sleep(8)
                continue
            txt = r.text.strip()
            if not txt:
                return []
            rows = json.loads(txt)
            return rows[1:] if rows else []
        except Exception as e:
            print("  CDX 异常 %s %s" % (url, repr(e)[:120]), flush=True)
            time.sleep(8)
    return []


summary = {}
for tag, url, match in TARGETS:
    rows = cdx(url, match)
    print("%-22s %-40s %d 条" % (tag, url, len(rows)), flush=True)
    for r in rows[:6]:
        print("   ", " | ".join(str(x) for x in r), flush=True)
    summary[tag] = {"url": url, "match": match, "count": len(rows), "rows": rows}
    with open(os.path.join(OUT, "%s.json" % tag), "w", encoding="utf-8") as f:
        json.dump({"url": url, "rows": rows}, f, ensure_ascii=False, indent=1)
    time.sleep(3)

with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
    json.dump({k: {"url": v["url"], "count": v["count"]} for k, v in summary.items()}, f,
              ensure_ascii=False, indent=1)
print("done", flush=True)
