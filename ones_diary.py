#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只抓 ONE's 的 FC2 日记全量快照。"""
import json
import os
import re
import time

import requests

CDX = "https://web.archive.org/cdx/search/cdx"
WB = "https://web.archive.org/web"
OUT = "out/diary"
os.makedirs(OUT, exist_ok=True)

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (personal-archive/1.0)"})


def cdx(url, tries=6):
    for i in range(tries):
        try:
            r = S.get(CDX, params={
                "url": url, "matchType": "prefix", "output": "json",
                "fl": "timestamp,original,statuscode,length",
                "filter": "statuscode:200", "limit": "4000",
            }, timeout=240)
            if r.status_code == 200 and r.text.strip():
                rows = json.loads(r.text)
                return rows[1:] if rows else []
            print("  CDX -> %s (try %d)" % (r.status_code, i + 1), flush=True)
        except Exception as e:
            print("  CDX err %s (try %d)" % (repr(e)[:80], i + 1), flush=True)
        time.sleep(30)
    return []


rows = cdx("diary1.fc2.com/cgi-sys/ed.cgi/oneyunn79")
print("CDX 结果 %d 条" % len(rows), flush=True)
rows = [r for r in rows if r[0][:4] in ("2004", "2005", "2006", "2007", "2008", "2009")] \
       + [r for r in rows if r[0][:4] not in ("2004", "2005", "2006", "2007", "2008", "2009")][:2]
print("待抓 %d 条" % len(rows), flush=True)

man = []
for ts, orig, code, ln in rows:
    name = re.sub(r"[^0-9A-Za-z]+", "_", orig.split("oneyunn79", 1)[-1])[:50].strip("_") or "index"
    dst = os.path.join(OUT, "%s__%s.html" % (ts, name))
    ok = 0
    for a in range(3):
        try:
            r = S.get("%s/%sid_/%s" % (WB, ts, orig), timeout=120)
            if r.status_code == 200 and len(r.content) > 500:
                open(dst, "wb").write(r.content)
                ok = len(r.content)
                break
        except Exception:
            pass
        time.sleep(5)
    print("  %s %-55s %d" % (ts, orig[:55], ok), flush=True)
    man.append({"ts": ts, "url": orig, "bytes": ok, "file": os.path.basename(dst)})
    time.sleep(1.5)

json.dump(man, open("out/diary_manifest.json", "w"), ensure_ascii=False, indent=1)
print("完成 %d / %d" % (sum(1 for m in man if m["bytes"]), len(man)), flush=True)
