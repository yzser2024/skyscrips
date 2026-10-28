#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二批：只补图片素材（FC2 表情/天气/箭头、日记配图、母站图片、jbbs 皮肤）。
与 ones_ui_fetch.py 共用 out_ui 目录，已存在且非空的文件跳过。
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ones_ui_fetch import cdx, get, flat, OUT  # noqa


def grab(rows, sub, want=None):
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    best = {}
    for r in rows:
        if len(r) < 4 or r[3] != "200":
            continue
        u, ts = r[0], r[1]
        if want and not re.search(want, u):
            continue
        if u not in best or ts > best[u]:
            best[u] = ts
    man = []
    for u, ts in sorted(best.items()):
        name = flat(u)
        p = os.path.join(OUT, sub, name)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            man.append({"url": u, "ts": ts, "file": sub + "/" + name, "skip": 1})
            continue
        b = get("https://web.archive.org/web/%sid_/%s" % (ts, u))
        if b is None:
            continue
        open(p, "wb").write(b)
        man.append({"url": u, "ts": ts, "file": sub + "/" + name, "size": len(b)})
        print("  ok %7d %s" % (len(b), name), flush=True)
    return man


def main():
    os.makedirs(OUT, exist_ok=True)
    man = []
    for lab, url in (("fc2img", "diary1.fc2.com/img/"),
                     ("fc2user", "diary1.fc2.com/user/oneyunn79/"),
                     ("site", "oneyunn79.client.jp/")):
        print("=== CDX", url, flush=True)
        r = cdx(url, "prefix")
        print("  rows", len(r), flush=True)
        man += grab(r, lab)
    json.dump(man, open(os.path.join(OUT, "manifest2.json"), "w"), ensure_ascii=False, indent=1)
    print("total", len(man))


if __name__ == "__main__":
    main()
