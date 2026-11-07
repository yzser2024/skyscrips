#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日本论坛检索 第五轮：把第四轮浮现的四条线索落到实处

1. ニコニコ大百科「ONE's」词条：直连 403 / Wayback 429 → 走 r.jina.ai 文本代理
2. niconico「【ONE's】案山子島【ゆん】」sm42741897 详情 + 投稿者 + 该账号的「ONE's」系列
3. 「素敵サイトまとめ」（morino-rhythm.seesaa.net）——日本博客的好站合集
4. 标签页 one's 的 96 本视频清单
5. Yahoo 补搜 amorxxx79 / withr17 / seesaa
"""
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request

OUT = "out_jp5"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp5.txt"), "w", encoding="utf-8")


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
BUDGET = 1000


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
    return st, b.decode("utf-8", "replace")


def text_of(t, n=2000):
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = (t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
          .replace("&#39;", "'"))
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()[:n]


res = {}

# ---------- 1. 大百科词条（多种入口） ----------
dic = {}
ENTRIES = [
    ("jina", "https://r.jina.ai/https://dic.nicovideo.jp/a/one%27s"),
    ("jina2", "https://r.jina.ai/https://dic.nicovideo.jp/a/one's"),
    ("wb_avail", "http://archive.org/wayback/available?url=dic.nicovideo.jp/a/one%27s"),
    ("wb_ts", "https://web.archive.org/web/2023id_/https://dic.nicovideo.jp/a/one%27s"),
]
for tag, url in ENTRIES:
    ST, TXT = get(url, save="dic5_%s.txt" % tag)
    d = {"status": ST, "len": len(TXT or ""), "url": url}
    if TXT:
        d["text"] = TXT[:4000] if tag.startswith("jina") else text_of(TXT, 2000)
    dic[tag] = d
    log("[dic5] %-9s status=%s len=%s" % (tag, ST, d["len"]))
    time.sleep(2)
res["dic_ones"] = dic

# ---------- 2. niconico 视频与系列 ----------
NICO = [
    ("sm42741897", "https://www.nicovideo.jp/watch/sm42741897"),
    ("series428414", "https://www.nicovideo.jp/user/130464424/series/428414"),
    ("user130464424", "https://www.nicovideo.jp/user/130464424/video"),
    ("tag_ones_json", "https://www.nicovideo.jp/tag/one%27s"),
]
nico = {}
for tag, url in NICO:
    ST, TXT = get(url, save="nico5_%s.html" % tag)
    d = {"status": ST, "len": len(TXT or ""), "url": url}
    if TXT and ST == 200:
        d["text"] = text_of(TXT, 1500)
        for pat, key in [(r'"title":"(.{1,120}?)"', "title"),
                         (r'"description":"(.{0,600}?)","', "desc"),
                         (r'"registeredAt":"([^"]+)"', "registeredAt"),
                         (r'"viewCount":(\d+)', "views"),
                         (r'"userId":"?(\d+)', "userId"),
                         (r'"owner":\{"id":"?(\d+)', "ownerId")]:
            m = re.search(pat, TXT)
            if m:
                d[key] = m.group(1)
        d["titles"] = list(dict.fromkeys(re.findall(r'"title":"(.{1,90}?)"', TXT)))[:30]
    nico[tag] = d
    log("[nico5] %-14s status=%s title=%s n_titles=%s"
        % (tag, ST, str(d.get("title"))[:40], len(d.get("titles", []))))
    time.sleep(1)
res["nico5"] = nico

# ---------- 3. 素敵サイトまとめ ----------
SS = [
    ("morino", "https://morino-rhythm.seesaa.net/article/283644961.html"),
    ("morino_top", "https://morino-rhythm.seesaa.net/"),
]
ss = {}
for tag, url in SS:
    ST, TXT = get(url, save="seesaa_%s.html" % tag)
    d = {"status": ST, "len": len(TXT or ""), "url": url}
    if TXT and ST == 200:
        d["text"] = text_of(TXT, 3000)
        hits = []
        for kw in ["ONE", "withr", "ゆん", "rico", "geocities"]:
            for m in re.finditer(kw, TXT, re.I):
                s = max(0, m.start() - 150)
                hits.append(TXT[s:m.start() + 150])
        d["ctx"] = [text_of(h, 300) for h in hits[:8]]
    ss[tag] = d
    log("[seesaa] %-10s status=%s len=%s ctx=%s" % (tag, ST, d["len"], len(d.get("ctx", []))))
    time.sleep(1)
res["seesaa"] = ss

# ---------- 4. Yahoo 补搜 ----------
YJ = [
    '"amorxxx79"',
    '"withr17" サイト',
    'site:seesaa.net ONE\'s MIDI',
    '"ONE\'s" "案山子島"',
    '"ONE\'s" ワンズ MIDI サイト 管理人',
    'withr geocities 音楽 サイト 閉鎖',
    '"music.geocities.jp" "withr17" OR "withr79"',
]
yj = []
for q in YJ:
    url = ("https://search.yahoo.co.jp/search?p=" + urllib.parse.quote(q) + "&ei=UTF-8&n=30")
    ST, TXT = get(url, save="yj5_%d.html" % len(yj))
    d = {"q": q, "status": ST, "len": len(TXT or "")}
    if TXT and ST == 200:
        cnt = re.search(r"約([\d,]+)件", TXT)
        d["count"] = cnt.group(0) if cnt else None
        blocks = re.findall(
            r'<a href="(https?://[^"]+)" class="sw-Card__titleInner".*?<h3[^>]*>(?:<span>(.*?)</span>)?</h3>',
            TXT, re.S)
        d["hits"] = [{"url": u, "title": re.sub(r"<[^>]+>", "", ti or "").strip()[:120]}
                     for u, ti in blocks][:20]
    yj.append(d)
    log("[yj5] %-40s status=%s %s n=%s" % (q, ST, d.get("count"), len(d.get("hits", []))))
    time.sleep(2)
res["yahoo"] = yj

json.dump(res, open(os.path.join(OUT, "jp5.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("DONE elapsed=%.0fs" % (time.time() - T0))
