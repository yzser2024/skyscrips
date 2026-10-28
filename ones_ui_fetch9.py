#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 FC2 日记的整套皮肤图（表情 / 天气 / 日历箭头 / spacer）在 CDX 里列全，
能抓的都抓回来。只为确认「缺的那些到底有没有存档」。
"""
import json
import os
import time
import urllib.parse
import urllib.request

OUT = "out_ui"
CDX = "http://web.archive.org/cdx/search/cdx"


def cdx(url):
    q = {"url": url, "output": "json",
         "fl": "timestamp,original,statuscode,mimetype,length",
         "collapse": "urlkey", "limit": "800"}
    u = CDX + "?" + urllib.parse.urlencode(q)
    for i in range(6):
        try:
            with urllib.request.urlopen(u, timeout=60) as r:
                d = json.load(r)
            return d[1:] if d else []
        except Exception as e:
            print("cdx retry", i, e)
            time.sleep(12)
    return []


def grab(ts, url, dest):
    u = "https://web.archive.org/web/%sid_/%s" % (ts, url)
    for i in range(2):
        try:
            with urllib.request.urlopen(u, timeout=40) as r:
                b = r.read()
            if len(b) < 60:
                return False
            if not (b.startswith(b"GIF8") or b.startswith(b"\xff\xd8\xff") or b.startswith(b"\x89PNG")):
                return False
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(b)
            print("ok", len(b), url)
            return True
        except Exception as e:
            time.sleep(3)
    print("fail", url)
    return False


def main():
    os.makedirs(OUT + "/fc2img", exist_ok=True)
    rows = cdx("http://diary1.fc2.com/img/*")
    print("img/* 存档条目", len(rows))
    open(OUT + "/cdx_img.json", "w").write(json.dumps(rows, ensure_ascii=False, indent=1))
    best = {}
    for ts, orig, sc, mt, ln in rows:
        if sc != "200":
            continue
        if not re_img(orig):
            continue
        best.setdefault(orig, ts)
    print("唯一图片", len(best))
    for orig in sorted(best):
        print("  ", best[orig], orig)
    ok = 0
    for orig, ts in sorted(best.items()):
        name = orig.split("diary1.fc2.com/")[-1].replace("/", "_")
        dest = "%s/fc2img/diary1.fc2.com_%s" % (OUT, name)
        if os.path.exists(dest):
            continue
        if grab(ts, orig, dest):
            ok += 1
    print("新抓", ok)
    print("--- files ---")
    for f in sorted(os.listdir(OUT + "/fc2img")):
        print(f, os.path.getsize(os.path.join(OUT, "fc2img", f)))


def re_img(orig):
    return orig.lower().endswith((".gif", ".jpg", ".png"))


if __name__ == "__main__":
    main()
