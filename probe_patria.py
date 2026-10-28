#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_patria.py —— 只为确认《パティリア》目录下到底存了哪些文件
在 GitHub Actions 上运行（沙箱连不上 archive.org）

输出：
  cdx_patria.json     CDX 原始结果
  files/              下载到的 mid / 图片（若有）
  report.txt          人读清单
"""
import json
import os
import time
import urllib.parse

import requests

CDX = "http://web.archive.org/cdx/search/cdx"
WAY = "https://web.archive.org/web/%sid_/%s"

WANT = [
    "www.geocities.jp/amorxxx79/patria/",
    "www.geocities.jp/amorxxx79/",
]

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (compatible; patria-probe/1.0)"})


def cdx(prefix, tries=4):
    params = {
        "url": prefix,
        "matchType": "prefix",
        "output": "json",
        "limit": "20000",
        "fl": "timestamp,original,mimetype,statuscode,length,digest",
    }
    for i in range(tries):
        try:
            r = S.get(CDX, params=params, timeout=120)
            if r.status_code == 200:
                txt = r.text.strip()
                if not txt:
                    return []
                rows = json.loads(txt)
                if not rows:
                    return []
                head = rows[0]
                return [dict(zip(head, x)) for x in rows[1:]]
            print("CDX HTTP %d for %s" % (r.status_code, prefix), flush=True)
        except Exception as e:
            print("CDX err %r" % (e,), flush=True)
        time.sleep(2 + i * 3)
    return []


def main():
    os.makedirs("files", exist_ok=True)
    all_rows = []
    report = []
    for p in WANT:
        rows = cdx(p)
        print("\n### %s -> %d 条" % (p, len(rows)), flush=True)
        all_rows.extend(rows)
        for r in rows:
            print("  %-12s %-8s %-10s %s" % (r.get("mimetype", ""), r.get("statuscode", ""),
                                             r.get("length", ""), r.get("original", "")), flush=True)

    json.dump(all_rows, open("cdx_patria.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # 需要下载的：mid / mp3 / 图片 / 其它非 HTML
    groups = {}
    for r in all_rows:
        if str(r.get("statuscode")) not in ("200", "-"):
            continue
        u = r["original"]
        low = urllib.parse.urlsplit(u).path.lower()
        if low.endswith((".html", ".htm", ".css", ".js", ".txt", ".gif")):
            continue
        if not low.endswith((".mid", ".midi", ".mp3", ".jpg", ".jpeg", ".png", ".lzh", ".zip")):
            continue
        groups.setdefault(u, []).append(r)

    print("\n非 HTML 候选 %d 个" % len(groups), flush=True)
    for u, lst in groups.items():
        lst.sort(key=lambda x: x["timestamp"])
        it = lst[-1]
        name = urllib.parse.unquote(urllib.parse.urlsplit(u).path).lstrip("/").replace("/", "__")
        dst = os.path.join("files", name)
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            report.append((u, it["timestamp"], os.path.getsize(dst), "cached"))
            continue
        src = WAY % (it["timestamp"], u)
        for i in range(4):
            try:
                r = S.get(src, timeout=180, allow_redirects=True)
                if r.status_code == 200 and r.content:
                    open(dst, "wb").write(r.content)
                    report.append((u, it["timestamp"], len(r.content), "ok"))
                    print("  saved %s (%d bytes)" % (name, len(r.content)), flush=True)
                    break
                print("  HTTP %d %s" % (r.status_code, u), flush=True)
            except Exception as e:
                print("  err %r %s" % (e, u), flush=True)
            time.sleep(2 + i * 2)
        else:
            report.append((u, it["timestamp"], 0, "fail"))

    with open("report.txt", "w", encoding="utf-8") as f:
        f.write("URL\t快照时间\t大小\t状态\n")
        for u, ts, sz, st in report:
            f.write("%s\t%s\t%d\t%s\n" % (u, ts, sz, st))
        f.write("\nCDX 总条目：%d\n" % len(all_rows))
    print("\n==== report ====")
    print(open("report.txt", encoding="utf-8").read())


if __name__ == "__main__":
    main()
