#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日本论坛检索 第八轮（收尾）

1. hayato 的「ONE's」系列：RSS + 逐个 getthumbinfo，把曲目、日期、播放数坐实
2. 大百科词条末段：切「With R」之后的句子
3. 查有没有「With R」「ゆん」的独立词条
4. 再确认一次 5ch / したらば 侧是否真的零结果
"""
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request

OUT = "out_jp8"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp8.txt"), "w", encoding="utf-8")


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
BUDGET = 800


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


res = {}

# ---------- 1. hayato 系列 ----------
ser = {}
for tag, url in [
    ("series_rss", "https://www.nicovideo.jp/user/130464424/series/428414?rss=2.0"),
    ("user_rss", "https://www.nicovideo.jp/user/130464424/video?rss=2.0"),
    ("mylist_rss", "https://www.nicovideo.jp/mylist/75716209?rss=2.0"),
]:
    ST, TXT = get(url, save="ser_%s.xml" % tag)
    d = {"status": ST, "len": len(TXT or "")}
    if TXT:
        items = re.findall(r"<item>(.*?)</item>", TXT, re.S)
        rows = []
        for it in items:
            f = lambda k: (re.search(r"<%s>(.*?)</%s>" % (k, k), it, re.S) or [None, ""])[1]
            rows.append({"title": re.sub(r"<!\[CDATA\[|\]\]>", "", f("title")).strip()[:100],
                         "link": f("link").strip(),
                         "date": f("pubDate").strip(),
                         "desc": re.sub(r"<!\[CDATA\[|\]\]>", "", f("description")).strip()[:200]})
        d["items"] = rows
        d["n"] = len(rows)
    ser[tag] = d
    log("[ser] %-11s status=%s items=%s" % (tag, ST, d.get("n")))
    time.sleep(1)
res["hayato"] = ser

# ---------- 2. 逐个 getthumbinfo ----------
VIDS = ["sm42741897", "sm42755385", "sm42755628", "sm42755723", "sm42755712"]
th = {}
for v in VIDS:
    ST, TXT = get("https://ext.nicovideo.jp/api/getthumbinfo/" + v, save="th8_%s.xml" % v)
    d = {"status": ST}
    for tagx in ["title", "description", "first_retrieve", "view_counter",
                 "comment_num", "mylist_counter", "length", "user_id"]:
        m = re.search(r"<%s>(.*?)</%s>" % (tagx, tagx), TXT or "", re.S)
        if m:
            d[tagx] = re.sub(r"\s+", " ", m.group(1)).strip()[:300]
    th[v] = d
    log("[th8] %-12s %s | %s | %s" % (v, d.get("status"), d.get("first_retrieve"), d.get("title")))
    time.sleep(0.8)
res["videos"] = th

# ---------- 3. 词条末段 + 别的词条 ----------
YJ = [
    'site:dic.nicovideo.jp "With R"',
    '"ONE\'s" "閉鎖" "With R" "ゆん" 大百科',
    'site:dic.nicovideo.jp "100点近い"',
    '"ONE\'s" "100点近いオリジナル楽曲"',
    'site:dic.nicovideo.jp "案山子島"',
]
yj = []
for q in YJ:
    url = ("https://search.yahoo.co.jp/search?p=" + urllib.parse.quote(q) + "&ei=UTF-8&n=30")
    ST, TXT = get(url, save="yj8_%d.html" % len(yj))
    d = {"q": q, "status": ST}
    if TXT and ST == 200:
        cnt = re.search(r"約([\d,]+)件", TXT)
        d["count"] = cnt.group(0) if cnt else None
        rows = []
        for m in re.finditer(r'<div class="sw-Card__title"><a href="(https?://[^"]+)"', TXT):
            seg = TXT[m.start():m.start() + 3500]
            ti = re.search(r"<h3[^>]*>(.*?)</h3>", seg, re.S)
            s2 = re.sub(r"<script.*?</script>", "", seg, flags=re.S)
            s2 = re.sub(r"<[^>]+>", "|", s2)
            s2 = re.sub(r"\|{2,}", "|", s2)
            rows.append({"url": m.group(1),
                         "title": re.sub(r"<[^>]+>", "", ti.group(1)).strip()[:100] if ti else "",
                         "desc": s2[:450]})
        d["hits"] = rows[:20]
    yj.append(d)
    log("[yj8] %-40s status=%s %s n=%s" % (q, ST, d.get("count"), len(d.get("hits", []))))
    time.sleep(2)
res["yahoo"] = yj

# ---------- 4. 5ch / したらば 复核 ----------
BBS = {}
for q in ["withr", "ONE's MIDI", "案山子島"]:
    url = "https://find.5ch.net/search?q=" + urllib.parse.quote(q)
    ST, TXT = get(url, save="f5_8_%d.html" % len(BBS))
    d = {"status": ST, "len": len(TXT or "")}
    if TXT and ST == 200:
        d["no_result"] = "No results found" in TXT
        th8 = re.findall(r'href="(//[a-z0-9.]*5ch\.io/test/read\.cgi/[^"]+)"[^>]*>(.*?)</a>', TXT, re.S)
        d["threads"] = [{"url": u, "title": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()[:90]}
                        for u, t in th8[:15]]
        d["n"] = len(d["threads"])
    BBS[q] = d
    log("[5ch8] %-12s status=%s noresult=%s threads=%s" % (q, ST, d.get("no_result"), d.get("n")))
    time.sleep(1)
res["5ch"] = BBS

json.dump(res, open(os.path.join(OUT, "jp8.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("DONE elapsed=%.0fs" % (time.time() - T0))
