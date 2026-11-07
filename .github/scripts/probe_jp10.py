#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十轮：抓 note「質問への返信」一文的提问原文（QA embed）

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

OUT = "out_jp10"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp10.txt"), "w", encoding="utf-8")


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


TARGETS = [
    ("qa_embed.html", "https://note.com/qa/embed/tristeza417/q/273c254eea4a5a6434bc8918d29df78d"),
    ("qa_page.html", "https://note.com/qa/tristeza417/q/273c254eea4a5a6434bc8918d29df78d"),
    ("api_note.json", "https://note.com/api/v3/notes/n14c4601353c0"),
    ("api_qa.json", "https://note.com/api/v3/qa/questions/273c254eea4a5a6434bc8918d29df78d"),
    ("qa_list.html", "https://note.com/qa/tristeza417"),
]

for fn, url in TARGETS:
    st, txt = get(url, save=fn)
    n = len(txt) if txt else 0
    log("%s  %s  %s  %d bytes" % (st, fn, url, n))
    RESULT.append({"file": fn, "url": url, "status": st, "bytes": n})
    if st == 200 and txt:
        # 打印可读文本摘要，便于在 log 里直接看
        plain = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", txt, flags=re.S)
        plain = re.sub(r"<[^>]+>", " ", plain)
        plain = re.sub(r"\s+", " ", plain).strip()
        log("   TEXT: " + plain[:1500])
    time.sleep(1)

json.dump(RESULT, open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("done")
