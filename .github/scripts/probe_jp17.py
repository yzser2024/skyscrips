#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十七轮：TRISTEZA 全站清点

A. 自站 tristeza.web.fc2.com 现存页面（含 album / midi 两栏）
B. Wayback CDX 全量清单（含 .mid / .mp3 二进制）
C. note 全部文章清单（137 篇）
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_jp17"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp17.txt"), "w", encoding="utf-8")


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
BUDGET = 1500
RESULT = []


def dec(b):
    for enc in ("utf-8", "cp932", "euc-jp"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", "replace"), "utf-8/replace"


def get(url, save=None, timeout=45, extra=None):
    if time.time() - T0 > BUDGET:
        return "SKIP", "", ""
    h = {"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"}
    if extra:
        h.update(extra)
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
        return None, "%s: %s" % (type(e).__name__, e), ""
    if save:
        open(os.path.join(RAW, save), "wb").write(b)
    txt, enc = dec(b)
    return st, txt, enc


def probe(url, save, label):
    st, txt, enc = get(url, save=save)
    n = len(txt) if txt else 0
    bad = ("404 Error" in txt[:3000]) if txt else False
    log("%-6s %-40s %s %6d bytes enc=%s%s" % (
        st, save, url[-45:], n, enc, "  [404-page]" if bad else ""))
    RESULT.append({"label": label, "url": url, "file": save, "status": st,
                   "bytes": n, "enc": enc, "is404": bad})
    time.sleep(0.8)
    return txt


log("=" * 70)
log("A. 自站现存页面")
log("=" * 70)
BASE = "http://tristeza.web.fc2.com/"
pages = [
    ("index.html", "首页"),
    ("album1.html", "album 栏"),
    ("12345.html", "midi 栏"),
    ("mp3.html", "mp3 猜测"),
    ("midi.html", "midi 猜测"),
    ("memo.html", "memo 猜测"),
    ("album.html", "album 猜测"),
    ("album2.html", "album2"),
    ("link.html", "link"),
    ("profile.html", "profile"),
    ("about.html", "about"),
    ("diary.html", "diary"),
    ("bbs.html", "bbs"),
    ("photo.html", "photo"),
    ("poem.html", "poem"),
]
for fn, label in pages:
    probe(BASE + fn, "fc2_" + fn.replace(".html", "") + ".html", label)

log("")
log("=" * 70)
log("B. Wayback CDX")
log("=" * 70)
CDX = "https://web.archive.org/cdx/search/cdx"
queries = [
    ("cdx_all.json",
     {"url": "tristeza.web.fc2.com", "matchType": "domain", "output": "json",
      "fl": "timestamp,original,statuscode,mimetype,length",
      "collapse": "urlkey", "limit": "20000"}),
    ("cdx_audio.json",
     {"url": "tristeza.web.fc2.com", "matchType": "domain", "output": "json",
      "fl": "timestamp,original,statuscode,mimetype,length",
      "filter": "mimetype:audio/.*", "limit": "5000"}),
    ("cdx_mid.json",
     {"url": "tristeza.web.fc2.com", "matchType": "domain", "output": "json",
      "fl": "timestamp,original,statuscode,mimetype,length",
      "filter": "original:.*\\.(mid|midi)$", "limit": "5000"}),
    ("cdx_mp3.json",
     {"url": "tristeza.web.fc2.com", "matchType": "domain", "output": "json",
      "fl": "timestamp,original,statuscode,mimetype,length",
      "filter": "original:.*\\.(mp3|wav|zip|m4a|ogg)$", "limit": "5000"}),
]
for fn, params in queries:
    u = CDX + "?" + urllib.parse.urlencode(params)
    st, txt, enc = get(u, save=fn, timeout=120)
    rows = 0
    if st == 200 and txt:
        try:
            rows = len(json.loads(txt))
        except Exception:
            rows = -1
    log("%-6s %-18s rows=%s  %d bytes" % (st, fn, rows, len(txt or "")))
    RESULT.append({"label": "cdx", "url": u, "file": fn, "status": st,
                   "bytes": len(txt or ""), "rows": rows})
    time.sleep(2)

log("")
log("=" * 70)
log("C. note 文章清单")
log("=" * 70)
note_tries = [
    ("note_v3_notes_p%d.json", "https://note.com/api/v3/creators/tristeza417/notes?page=%d&per=20"),
    ("note_v2_contents_p%d.json", "https://note.com/api/v2/creators/tristeza417/contents?kind=note&page=%d&per=10"),
]
hit = None
for tpl, url_tpl in note_tries:
    st, txt, enc = get(url_tpl % 1, save=(tpl % 1))
    n = 0
    try:
        d = json.loads(txt)
        dd = d.get("data", d)
        if isinstance(dd, dict):
            for k in ("notes", "contents", "data"):
                if isinstance(dd.get(k), list):
                    n = len(dd[k])
                    break
        elif isinstance(dd, list):
            n = len(dd)
    except Exception:
        pass
    log("%-6s %-28s items=%d" % (st, tpl % 1, n))
    if st == 200 and n > 0:
        hit = (tpl, url_tpl)
        break

if hit:
    tpl, url_tpl = hit
    for p in range(2, 10):
        st, txt, enc = get(url_tpl % p, save=(tpl % p))
        n = 0
        try:
            d = json.loads(txt)["data"]
            for k in ("notes", "contents", "data"):
                if isinstance(d.get(k) if isinstance(d, dict) else None, list):
                    n = len(d[k])
                    break
        except Exception:
            pass
        log("  page %d  %s  items=%d" % (p, st, n))
        if n == 0:
            break
        time.sleep(0.7)

log("")
log("D. note sitemap / 旧 note.mu")
for fn, u in [("note_sitemap.xml", "https://note.com/tristeza417/sitemap.xml"),
              ("note_mu_index.html", "https://note.mu/tristeza417")]:
    st, txt, enc = get(u, save=fn)
    log("%-6s %-24s %d bytes" % (st, fn, len(txt or "")))

json.dump(RESULT, open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("done in %ds" % int(time.time() - T0))
