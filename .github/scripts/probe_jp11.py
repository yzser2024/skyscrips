#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十一轮：抓 TRISTEZA 全部 18 篇文章的 API JSON，检索是否另有提及 ONE's / With R / ゆん

文章 https://note.com/tristeza417/n/n14c4601353c0
内嵌提问 https://note.com/qa/tristeza417/q/273c254eea4a5a6434bc8918d29df78d
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request

OUT = "out_jp11"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp11.txt"), "w", encoding="utf-8")


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
BUDGET = 600

RESULT = []


def get(url, headers=None, timeout=40, save=None):
    if time.time() - T0 > BUDGET:
        return "SKIP", ""
    h = {"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
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
        return None, "%s: %s" % (type(e).__name__, e)
    if save:
        open(os.path.join(RAW, save), "wb").write(b)
    try:
        return st, b.decode("utf-8")
    except UnicodeDecodeError:
        return st, b.decode("utf-8", "replace")



TARGETS = []
for k in ['ne054a8cab305', 'n676a828317ba', 'n14c4601353c0', 'nb055a831c232', 'n3d8d4b8677e2', 'nce8003278704', 'nbce9dd341631', 'nfdd61ad69715', 'nb623d80cf89f', 'nc6bb701eb53f', 'n50cdd0a2dcaf', 'n97b568718c5b', 'n706457627ccd', 'n537d733e4fc9', 'n85b4fcb7e740', 'ne560a120cb3f', 'n82648e22c81f', 'n3a1bd2ec9006']:
    TARGETS.append(("%s.json" % k, "https://note.com/api/v3/notes/%s" % k))

HITS = []
for fn, url in TARGETS:
    st, txt = get(url, save=fn)
    n = len(txt) if txt else 0
    log("%s  %s  %d bytes" % (st, fn, n))
    RESULT.append({"file": fn, "url": url, "status": st, "bytes": n})
    if st == 200 and txt:
        for kw in ["ONE", "With R", "withr", "ゆん", "yunn", "別館"]:
            if kw in txt:
                HITS.append({"file": fn, "kw": kw})
                log("   HIT %s in %s" % (kw, fn))
    time.sleep(1)

json.dump(RESULT, open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(HITS, open(os.path.join(OUT, "hits.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("done")
