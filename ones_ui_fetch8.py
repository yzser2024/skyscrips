#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查 FC2 日记图库的全部存档，并把缺的那张（2004_11/5.jpg）抓回来。
CDX 带重试；抓图带硬超时；只存真图（按魔数）。
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_ui"
CDX = "http://web.archive.org/cdx/search/cdx"


def cdx(url, extra=""):
    q = {"url": url, "output": "json",
         "fl": "timestamp,original,statuscode,mimetype,length",
         "collapse": "urlkey", "limit": "400"}
    u = CDX + "?" + urllib.parse.urlencode(q) + extra
    for i in range(6):
        try:
            with urllib.request.urlopen(u, timeout=60) as r:
                d = json.load(r)
            return d[1:] if d else []
        except Exception as e:
            print("cdx retry", i, e)
            time.sleep(15)
    return []


def grab(ts, url, dest):
    u = "https://web.archive.org/web/%sid_/%s" % (ts, url)
    try:
        with urllib.request.urlopen(u, timeout=45) as r:
            b = r.read()
    except Exception as e:
        print("fail", url, e)
        return False
    if len(b) < 200:
        return False
    if not (b.startswith(b"\xff\xd8\xff") or b.startswith(b"GIF8") or b.startswith(b"\x89PNG")):
        print("not an image", url, len(b))
        return False
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "wb").write(b)
    print("ok", len(b), url)
    return True


def main():
    os.makedirs(OUT + "/fc2user", exist_ok=True)
    rows = []
    for pat in ("http://diary1.fc2.com/user/oneyunn79/img/*",
                "http://diary1.fc2.com/cgi/fitImg.cgi?i=oneyunn79*"):
        r = cdx(pat)
        print(pat, len(r))
        rows += r
    open(OUT + "/cdx_user.json", "w").write(json.dumps(rows, ensure_ascii=False, indent=1))
    # 全部存档清单
    seen = set()
    for ts, orig, sc, mt, ln in rows:
        if orig in seen:
            continue
        seen.add(orig)
        print("  ", ts, sc, mt, ln, orig)

    # 抓到手的原图（按 URL）
    imgs = {}
    for ts, orig, sc, mt, ln in rows:
        if "/user/oneyunn79/img/" not in orig:
            continue
        if sc != "200":
            continue
        imgs.setdefault(orig, ts)

    todo = []
    for orig, ts in imgs.items():
        name = orig.split("/user/oneyunn79/img/")[1].replace("/", "_")
        dest = "%s/fc2user/diary1.fc2.com_user_oneyunn79_img_%s" % (OUT, name)
        if os.path.exists(dest):
            continue
        todo.append((ts, orig, dest))
    print("待抓", len(todo))
    ok = 0
    for ts, orig, dest in todo[:20]:
        if grab(ts, orig, dest):
            ok += 1
    print("成功", ok, "/", len(todo))
    print("--- files ---")
    for f in sorted(os.listdir(OUT + "/fc2user")):
        print(f, os.path.getsize(os.path.join(OUT, "fc2user", f)))


if __name__ == "__main__":
    main()
