#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deep29: 取回 geocities 日记页引用的照片、装饰 gif 与样式表。"""
import gzip
import json
import os
import ssl
import time
import urllib.error
import urllib.request

OUT = "out_deep29"
os.makedirs(OUT + "/img", exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# (保存名, 原站相对路径)
TARGETS = [("1.jpg", "diary/1.jpg"), ("2.jpg", "diary/2.jpg"),
           ("3.jpg", "diary/3.jpg"), ("4.jpg", "diary/4.jpg"),
           ("5.jpg", "diary/5.jpg"), ("6.jpg", "diary/6.jpg"),
           ("7.jpg", "diary/7.jpg"), ("8.jpg", "diary/8.jpg"),
           ("line_diary.gif", "line_diary.gif"), ("point.gif", "point.gif"),
           ("css.css", "css.css")]

STAMPS = ["20080226134311", "20080430134421", "20080226134311js_", ""]
BASE = "http://www.geocities.jp/amorxxx79/"
log = []


def fetch(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "*/*", "Referer": "http://web.archive.org/"})
            with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                b = r.read()
            if b[:2] == b"\x1f\x8b" and not url.endswith((".gif", ".css")):
                try:
                    b = gzip.decompress(b)
                except Exception:
                    pass
            return b, r.geturl()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                time.sleep(3 + i * 4); continue
            return None, "HTTP %s" % e.code
        except Exception as e:
            time.sleep(2 + i * 3)
            last = str(e)[:50]
    return None, "fail"


def main():
    for name, rel in TARGETS:
        got = None
        src = ""
        for st in STAMPS:
            u = "http://web.archive.org/web/%sid_/%s%s" % (st, BASE, rel)
            b, real = fetch(u)
            if b and len(b) > 120:
                got, src = b, real
                break
        if got:
            p = "%s/img/%s" % (OUT, name)
            open(p, "wb").write(got)
            log.append("OK   %-16s %7d 字节  from %s" % (name, len(got), src[-70:]))
        else:
            log.append("MISS %-16s %s" % (name, src))
    print("\n".join(log))
    open(OUT + "/log.txt", "w", encoding="utf-8").write("\n".join(log))


if __name__ == "__main__":
    main()
