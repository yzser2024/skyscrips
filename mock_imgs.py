#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载 ucaliy「Mock Diary」的配图：先试原 CDN，失败再走 Wayback im_。"""

import json
import os
import time

import requests

OUT = "imgs"
os.makedirs(OUT, exist_ok=True)

S = requests.Session()
S.headers.update({
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Referer": "https://ucaliy.tumblr.com/",
})

items = json.load(open("mock_imgs.json", encoding="utf-8"))
print("待下载 %d 张" % len(items), flush=True)

ok = fail = skip = 0
report = []

for i, it in enumerate(items, 1):
    url, ts = it["url"], it.get("ts", "2")
    name = url.split("?")[0].rstrip("/").split("/")[-1]
    dst = os.path.join(OUT, name)
    if os.path.exists(dst) and os.path.getsize(dst) > 1000:
        skip += 1
        continue

    got = False
    # 1) 原 CDN
    try:
        r = S.get(url, timeout=40)
        if r.status_code == 200 and len(r.content) > 1000 and "image" in r.headers.get("Content-Type", ""):
            open(dst, "wb").write(r.content)
            got = True
            report.append({"file": name, "src": "cdn", "bytes": len(r.content)})
    except Exception:
        pass

    # 2) Wayback im_
    if not got:
        for t in (ts, "2", "2018"):
            try:
                r = S.get("https://web.archive.org/web/%sim_/%s" % (t, url), timeout=60)
                if r.status_code == 200 and len(r.content) > 1000:
                    open(dst, "wb").write(r.content)
                    got = True
                    report.append({"file": name, "src": "wayback:" + t, "bytes": len(r.content)})
                    break
            except Exception:
                continue

    if got:
        ok += 1
    else:
        fail += 1
        report.append({"file": name, "src": "FAIL", "url": url})

    if i % 10 == 0:
        print("  %d/%d  ok=%d fail=%d" % (i, len(items), ok, fail), flush=True)
    time.sleep(0.3)

json.dump(report, open("imgs_report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("完成：成功 %d，失败 %d，跳过 %d" % (ok, fail, skip), flush=True)
