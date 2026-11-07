#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日本论坛检索 第九轮（补全）

1. Yahoo 翻页，把 hayato「【ONE's】…【ゆん】」系列曲目尽量列全
2. 确认ニコニコ大百科是否另有「With R」词条
3. 确认 5ch 对 withr17 / oneyunn 的零结果状态
"""
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request

OUT = "out_jp9"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp9.txt"), "w", encoding="utf-8")


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
BUDGET = 700


def get(url, headers=None, timeout=30, save=None):
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
    return st, b.decode("utf-8", "replace")


def yahoo(q, b=1, save=None):
    url = ("https://search.yahoo.co.jp/search?p=" + urllib.parse.quote(q)
           + "&ei=UTF-8&n=30&b=%d" % b)
    ST, TXT = get(url, save=save)
    rows = []
    cnt = None
    if TXT and ST == 200:
        m = re.search(r"約([\d,]+)件", TXT)
        cnt = m.group(0) if m else None
        for mm in re.finditer(r'<div class="sw-Card__title"><a href="(https?://[^"]+)"', TXT):
            seg = TXT[mm.start():mm.start() + 3000]
            ti = re.search(r"<h3[^>]*>(.*?)</h3>", seg, re.S)
            s2 = re.sub(r"<script.*?</script>", "", seg, flags=re.S)
            s2 = re.sub(r"<[^>]+>", "|", s2)
            s2 = re.sub(r"\|{2,}", "|", s2)
            rows.append({"url": mm.group(1),
                         "title": re.sub(r"<[^>]+>", "", ti.group(1)).strip()[:110] if ti else "",
                         "desc": s2[:400]})
    return {"q": q, "b": b, "status": ST, "count": cnt, "hits": rows}


res = {}

# ---------- 1. hayato 系列：两页 ----------
p1 = yahoo('"【ONE\'s】" "ゆん" site:nicovideo.jp', 1, "yj9_p1.html")
p2 = yahoo('"【ONE\'s】" "ゆん" site:nicovideo.jp', 11, "yj9_p2.html")
p3 = yahoo('"【ONE\'s】" ニコニコ ゆん', 1, "yj9_p3.html")
res["hayato"] = [p1, p2, p3]
for p in (p1, p2, p3):
    log("[y9] b=%-2s %s n=%s" % (p["b"], p["count"], len(p["hits"])))

# ---------- 2. With R 词条 ----------
wr = []
for q in ['site:dic.nicovideo.jp "With R" 楽曲 サイト',
          '"With R" 単語記事 ニコニコ大百科 MIDI',
          'site:dic.nicovideo.jp "With R" "SoundCloud"']:
    r = yahoo(q, 1, "yj9_wr_%d.html" % len(wr))
    wr.append(r)
    log("[y9wr] %-44s %s n=%s" % (q, r["count"], len(r["hits"])))
res["withr_dic"] = wr

# ---------- 3. 5ch 复核 ----------
f5 = {}
for q in ["withr17", "oneyunn", "yunn"]:
    url = "https://find.5ch.net/search?q=" + urllib.parse.quote(q)
    ST, TXT = get(url, save="f5_9_%s.html" % q)
    d = {"status": ST, "noresult": ("No results found" in (TXT or ""))}
    if TXT and ST == 200:
        th = re.findall(r'href="(//[a-z0-9.]*5ch\.io/test/read\.cgi/[^"]+)"[^>]*>(.*?)</a>', TXT, re.S)
        d["titles"] = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()[:70] for _, t in th[:8]]
    f5[q] = d
    log("[5ch9] %-10s status=%s noresult=%s" % (q, ST, d.get("noresult")))
    time.sleep(1)
res["5ch"] = f5

json.dump(res, open(os.path.join(OUT, "jp9.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("DONE elapsed=%.0fs" % (time.time() - T0))
