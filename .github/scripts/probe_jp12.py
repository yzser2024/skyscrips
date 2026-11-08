#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十二轮：确认 note 作者 TRISTEZA 是谁

1. 自站 http://tristeza.web.fc2.com/ 首页与常见栏目
2. note 作者资料 API 与文章清单（拿全部标题，看她写什么）
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request

OUT = "out_jp12"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp12.txt"), "w", encoding="utf-8")


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
T0 = time.time()
BUDGET = 500
RESULT = []


def dec(b):
    for enc in ("utf-8", "cp932", "euc-jp"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", "replace"), "utf-8/replace"


def get(url, save=None, timeout=35):
    if time.time() - T0 > BUDGET:
        return "SKIP", "", ""
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                              "Accept-Language": "ja,en;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            b, st = r.read(), r.status
    except urllib.error.HTTPError as e:
        try:
            b = e.read()
        except Exception:
            b = b""
        st = e.code
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e), ""
    if save:
        open(os.path.join(RAW, save), "wb").write(b)
    txt, enc = dec(b)
    return st, txt, enc


TARGETS = [
    ("fc2_index.html", "http://tristeza.web.fc2.com/"),
    ("fc2_profile.html", "http://tristeza.web.fc2.com/profile.html"),
    ("fc2_about.html", "http://tristeza.web.fc2.com/about.html"),
    ("creator_api.json", "https://note.com/api/v2/creators/tristeza417"),
    ("contents_p1.json", "https://note.com/api/v2/creators/tristeza417/contents?kind=note&page=1&per=50"),
    ("contents_p2.json", "https://note.com/api/v2/creators/tristeza417/contents?kind=note&page=2&per=50"),
    ("contents_p3.json", "https://note.com/api/v2/creators/tristeza417/contents?kind=note&page=3&per=50"),
]

for fn, url in TARGETS:
    st, txt, enc = get(url, save=fn)
    n = len(txt) if txt else 0
    log("%s  %s  %s  %d bytes  %s" % (st, fn, url, n, enc))
    RESULT.append({"file": fn, "url": url, "status": st, "bytes": n, "enc": enc})
    if st == 200 and txt and fn.startswith("fc2"):
        plain = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", txt, flags=re.S)
        plain = re.sub(r"<br\s*/?>", "\n", plain)
        plain = re.sub(r"<[^>]+>", " ", plain)
        plain = re.sub(r"[ \t]+", " ", plain)
        log("   TEXT: " + plain.strip()[:1200].replace("\n", " / "))
        # 首页内部链接
        if fn == "fc2_index.html":
            links = re.findall(r'href="([^"]+)"', txt)
            log("   LINKS: " + " | ".join(list(dict.fromkeys(links))[:25]))
    time.sleep(1)

json.dump(RESULT, open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("done")
