#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日本论坛 / 日本平台检索：niconico（视频 API、大百科、静画）、Yahoo!知恵袋、
5ch、したらば、2ch 过去日志、以及带 site: 限定的搜索引擎。

只记录「返回了什么」，不做判定。命中的标题/简介原文逐条保留。
"""
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request

OUT = "out_jp"
os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp.txt"), "w", encoding="utf-8")


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
T0 = time.time()
BUDGET = 1500  # 秒


def get(url, headers=None, timeout=25):
    if time.time() - T0 > BUDGET:
        return "SKIP", ""
    h = {"User-Agent": UA, "Accept-Language": "ja,en;q=0.8",
         "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            b = r.read()
            try:
                return r.status, b.decode("utf-8", "replace")
            except Exception:
                return r.status, b.decode("cp932", "replace")
    except urllib.error.HTTPError as e:
        try:
            b = e.read()
            return e.code, b.decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


res = {}

# ================= 1. niconico 视频搜索 API =================
API = ("https://api.search.nicovideo.jp/api/v2/snapshot/video/contents/search"
       "?q=%s&targets=title,description,tags&fields=contentId,title,description,"
       "tags,viewCounter,commentCounter,mylistCounter,startTime,lengthSeconds,"
       "userId,channelId&_sort=-viewCounter&_limit=50&_context=withr_research")

NICO_Q = [
    ("withr", "withr"),
    ("withr17", "withr17"),
    ('"With R"', '"With R"'),
    ("yunn", "yunn"),
    ("ゆん", "ゆん"),
    ("oneyunn", "oneyunn"),
    ("案山子島", "案山子島"),
    ('"ONE\'s"', "ONE's"),
    ("withr+rico", "withr rico"),
    ("曇一", "曇一"),
]

nico_hits = []
for label, q in NICO_Q:
    url = API % urllib.parse.quote(q)
    st, txt = get(url)
    item = {"query": label, "status": st, "len": len(txt or "")}
    try:
        j = json.loads(txt)
        meta = j.get("meta", {})
        item["total"] = meta.get("totalCount")
        data = j.get("data", [])
        item["n"] = len(data)
        rows = []
        for d in data:
            rows.append({
                "id": d.get("contentId"),
                "title": d.get("title"),
                "desc": (d.get("description") or "")[:600],
                "tags": d.get("tags"),
                "view": d.get("viewCounter"),
                "comment": d.get("commentCounter"),
                "mylist": d.get("mylistCounter"),
                "start": d.get("startTime"),
                "length": d.get("lengthSeconds"),
                "user": d.get("userId"),
            })
        item["rows"] = rows
        nico_hits.append(item)
        log("[nico] %-12s status=%s total=%s got=%s" % (label, st, item["total"], len(rows)))
    except Exception as e:
        item["err"] = str(e)
        item["raw"] = (txt or "")[:400]
        nico_hits.append(item)
        log("[nico] %-12s status=%s parse-fail %s" % (label, st, e))
    time.sleep(1.2)

res["niconico_search_api"] = nico_hits

# ================= 2. ニコニコ大百科 =================
DIC_Q = ["withr", "withr17", "yunn", "ゆん", "案山子島", "ONE's", "曇一"]
dic = []
for q in DIC_Q:
    url = "https://dic.nicovideo.jp/search/" + urllib.parse.quote(q)
    st, txt = get(url)
    d = {"q": q, "status": st, "len": len(txt or ""), "url": url}
    if txt and st == 200:
        # 结果条目：<a href="/a/XXXX">title</a>
        arts = re.findall(r'href="(/a/[^"]+)"[^>]*>([^<]{1,80})<', txt)
        d["articles"] = [{"path": a, "title": b.strip()} for a, b in arts][:15]
        m = re.search(r'([0-9,]+)\s*件', txt)
        if m:
            d["count_text"] = m.group(0)
        if not arts:
            d["note"] = "no <a href=/a/> match"
            d["head"] = re.sub(r"\s+", " ", txt[:800])
    dic.append(d)
    log("[dic] %-10s status=%s arts=%s" % (q, st, len(d.get("articles", []))))
    time.sleep(1)

res["nicopedia"] = dic

# ================= 3. ニコニコ静画 =================
seiga = []
for q in ["withr", "yunn", "案山子島"]:
    url = "https://seiga.nicovideo.jp/search/" + urllib.parse.quote(q)
    st, txt = get(url)
    d = {"q": q, "status": st, "len": len(txt or ""), "url": url}
    if txt and st == 200:
        titles = re.findall(r'class="title"[^>]*>\s*([^<]{1,80})', txt)
        d["titles"] = titles[:10]
        d["note"] = "JS-rendered" if not titles else ""
    seiga.append(d)
    log("[seiga] %-10s status=%s" % (q, st))
    time.sleep(1)

res["seiga"] = seiga

# ================= 4. Yahoo!知恵袋 =================
CHIE_Q = ["withr", "「With R」 音楽", "yunn 作曲", "ONE's MIDI", "案山子島 曲", "ゆん MIDI"]
chie = []
for q in CHIE_Q:
    url = ("https://chiebukuro.yahoo.co.jp/search?p=" + urllib.parse.quote(q)
           + "&ei=UTF-8&fl=1")
    st, txt = get(url)
    d = {"q": q, "status": st, "len": len(txt or ""), "url": url}
    if txt and st == 200:
        # 结果标题与摘要
        t = re.findall(r'<a[^>]+href="(https://detail\.chiebukuro\.yahoo\.co\.jp/[^"]+)"[^>]*>(.{0,160}?)</a>', txt, re.S)
        rows = []
        for u, s in t[:12]:
            s = re.sub(r"<[^>]+>", "", s)
            s = re.sub(r"\s+", " ", s).strip()
            if s:
                rows.append({"url": u.split("?")[0], "title": s})
        d["hits"] = rows
        d["note"] = "" if rows else "no detail link matched"
    chie.append(d)
    log("[chie] %-16s status=%s hits=%s" % (q, st, len(d.get("hits", []))))
    time.sleep(1)

res["chiebukuro"] = chie

# ================= 5. 5ch / したらば / 2ch 过去日志 =================
BBS = [
    ("find5ch_withr", "https://find.5ch.net/search?q=" + urllib.parse.quote("withr")),
    ("find5ch_yunn", "https://find.5ch.net/search?q=" + urllib.parse.quote("yunn")),
    ("find5ch_oneyunn", "https://find.5ch.net/search?q=" + urllib.parse.quote("oneyunn")),
    ("find5ch_kakashijima", "https://find.5ch.net/search?q=" + urllib.parse.quote("案山子島")),
    ("shitaraba_search", "https://rentalbbs.shitaraba.com/search/?q=" + urllib.parse.quote("withr")),
    ("futakuro_withr", "https://kako.futakuro.com/fate/?q=" + urllib.parse.quote("withr")),
    ("2chsc_search", "https://www.2ch.sc/search/?q=" + urllib.parse.quote("withr")),
]
bbs = {}
for k, url in BBS:
    st, txt = get(url, timeout=30)
    d = {"status": st, "len": len(txt or ""), "url": url}
    if txt and st == 200:
        d["head"] = re.sub(r"\s+", " ", re.sub(r"<script.*?</script>", "", txt, flags=re.S))[:700]
    bbs[k] = d
    log("[bbs] %-20s status=%s len=%s" % (k, st, d["len"]))
    time.sleep(1)

res["bbs"] = bbs

# ================= 6. site: 限定搜索引擎 =================
SE = [
    ("bing", 'site:nicovideo.jp withr'),
    ("bing", 'site:nicovideo.jp "With R" 音楽'),
    ("bing", 'site:dic.nicovideo.jp withr'),
    ("bing", 'site:5ch.net withr'),
    ("bing", 'site:5ch.net "With R" 音楽'),
    ("bing", '"music.geocities.jp/withr17"'),
    ("bing", '"oneyunn79"'),
    ("bing", '"案山子島" 曲'),
    ("ddg", 'site:nicovideo.jp withr'),
    ("ddg", '"music.geocities.jp/withr17"'),
    ("ddg", 'site:5ch.net withr'),
    ("ddg", '"With R" ゆん rico 曲'),
]
se = []
for eng, q in SE:
    if eng == "bing":
        url = ("https://www.bing.com/search?q=" + urllib.parse.quote(q)
               + "&count=30&setlang=ja&cc=JP")
    else:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q)
    st, txt = get(url, timeout=30)
    d = {"engine": eng, "q": q, "status": st, "len": len(txt or ""), "url": url}
    if txt and st == 200:
        if eng == "bing":
            items = re.findall(r'<li class="b_algo".*?<h2><a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', txt, re.S)
        else:
            items = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', txt, re.S)
        rows = []
        for u, t in items[:20]:
            t = re.sub(r"<[^>]+>", "", t)
            t = re.sub(r"\s+", " ", t).strip()
            rows.append({"url": u, "title": t})
        d["hits"] = rows
        if not rows:
            d["head"] = re.sub(r"\s+", " ", re.sub(r"<script.*?</script>", "", txt, flags=re.S))[:600]
    se.append(d)
    log("[se:%s] %-34s status=%s hits=%s" % (eng, q, st, len(d.get("hits", []))))
    time.sleep(1.5)

res["search_engines"] = se

# ================= 7. 具体视频页核对 =================
VIDS = ["nm10255152", "nm11669772"]
vid = {}
for v in VIDS:
    url = "https://www.nicovideo.jp/watch/" + v
    st, txt = get(url)
    d = {"status": st, "len": len(txt or ""), "url": url}
    if txt and st == 200:
        for pat, key in [(r'<title>([^<]+)</title>', "title"),
                         (r'"description":"(.{0,400}?)"', "desc")]:
            m = re.search(pat, txt)
            if m:
                d[key] = m.group(1)
    vid[v] = d
    log("[vid] %-12s status=%s" % (v, st))
    time.sleep(1)

res["videos"] = vid

json.dump(res, open(os.path.join(OUT, "jp.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("DONE elapsed=%.0fs" % (time.time() - T0))
