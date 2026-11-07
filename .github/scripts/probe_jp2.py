#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日本论坛检索 第二轮：换 UA / 换入口，重点是把「服务端渲染、能出结果」的日本站点抓下来。

1. niconico snapshot API 换 UA + 备用 host
2. ニコニコ大百科 直连条目页 / 站内搜索入口
3. Yahoo! JAPAN 搜索（服务端渲染，日文语料）
4. はてなブックマーク 搜索（日本社区聚合）
5. Yahoo!リアルタイム検索
6. find.5ch.net 保存原始 HTML + 提取 read.cgi 链接
7. Google（可能 429，如实记录）
8. 知恵袋那条「素材サイト」问答正文
"""
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request

OUT = "out_jp2"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp2.txt"), "w", encoding="utf-8")


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


UA_FF = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
         "(KHTML, like Gecko) Version/17.4 Safari/605.1.15")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
T0 = time.time()
BUDGET = 1200


def get(url, headers=None, timeout=30, save=None):
    if time.time() - T0 > BUDGET:
        return "SKIP", ""
    h = {"User-Agent": UA_FF,
         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
         "Accept-Language": "ja,en-US;q=0.7,en;q=0.3"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            b = r.read()
            st = r.status
    except urllib.error.HTTPError as e:
        try:
            b = e.read()
        except Exception:
            b = b""
        st = e.code
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)
    txt = b.decode("utf-8", "replace")
    if save:
        open(os.path.join(RAW, save), "wb").write(b)
    return st, txt


res = {}

# ---------- 1. niconico snapshot API ----------
API = ("https://api.search.nicovideo.jp/api/v2/snapshot/video/contents/search"
       "?q=%s&targets=title,description,tags&fields=contentId,title,description,"
       "tags,viewCounter,commentCounter,mylistCounter,startTime,lengthSeconds,userId"
       "&_sort=-viewCounter&_limit=50&_context=research")
NICO = [("withr", "withr"), ("withr17", "withr17"), ('"With R"', '"With R"'),
        ("yunn", "yunn"), ("ゆん", "ゆん"), ("oneyunn", "oneyunn"),
        ("案山子島", "案山子島"), ('"ONE\'s"', "ONE's"), ("曇一", "曇一"),
        ("rico+withr", "rico withr")]
nico = []
for label, q in NICO:
    url = API % urllib.parse.quote(q)
    st, txt = get(url, {"User-Agent": "WithR-Research/1.0 (+https://example.org/contact)"})
    d = {"query": label, "status": st, "len": len(txt or "")}
    try:
        j = json.loads(txt)
        d["total"] = j.get("meta", {}).get("totalCount")
        data = j.get("data", [])
        d["rows"] = [{"id": x.get("contentId"), "title": x.get("title"),
                      "desc": (x.get("description") or "")[:500],
                      "tags": x.get("tags"), "view": x.get("viewCounter"),
                      "comment": x.get("commentCounter"), "start": x.get("startTime")}
                     for x in data]
        d["n"] = len(data)
    except Exception as e:
        d["err"] = str(e)
        d["raw"] = (txt or "")[:300]
    nico.append(d)
    log("[nico2] %-12s status=%s total=%s n=%s" % (label, st, d.get("total"), d.get("n")))
    time.sleep(1)
res["nico_api"] = nico

# ---------- 2. ニコニコ大百科 ----------
dic = []
for path in ["/a/withr", "/a/withr17", "/a/yunn", "/a/%E3%82%86%E3%82%93",
             "/a/%E6%A1%88%E5%B1%B1%E5%AD%90%E5%B3%B6", "/a/ONE%27s"]:
    url = "https://dic.nicovideo.jp" + path
    st, txt = get(url, save="dic" + path.replace("/", "_")[:40] + ".html")
    d = {"url": url, "status": st, "len": len(txt or "")}
    if txt and st == 200:
        m = re.search(r"<title>([^<]+)</title>", txt)
        d["title"] = m.group(1) if m else ""
        body = re.sub(r"<script.*?</script>", "", txt, flags=re.S)
        body = re.sub(r"<[^>]+>", " ", body)
        d["head"] = re.sub(r"\s+", " ", body)[:400]
    dic.append(d)
    log("[dic2] %-40s status=%s" % (path, st))
    time.sleep(1)
res["dic"] = dic

# ---------- 3. Yahoo! JAPAN 搜索 ----------
YJ = ['"withr17"', '"music.geocities.jp/withr17"', '"oneyunn79"',
      'withr 音楽 サイト', '"案山子島" 曲 MIDI', 'yunn rico 作曲 サイト',
      '"With R" ONE\'s 別館']
yj = []
for q in YJ:
    url = ("https://search.yahoo.co.jp/search?p=" + urllib.parse.quote(q) + "&ei=UTF-8")
    st, txt = get(url, save="yj_" + str(abs(hash(q)) % 99999) + ".html")
    d = {"q": q, "status": st, "len": len(txt or ""), "url": url}
    if txt and st == 200:
        # Yahoo 结果：<a href="https://..."><span>...</span></a> 结构多变，先抓 h3
        items = re.findall(r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', txt, re.S)
        if not items:
            items = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>\s*<span[^>]*>(.*?)</span>', txt, re.S)
        rows = []
        for u, t in items[:20]:
            t = re.sub(r"<[^>]+>", "", t)
            t = re.sub(r"\s+", " ", t).strip()
            if t and "yahoo.co.jp" not in u[:60]:
                rows.append({"url": u[:200], "title": t[:120]})
        d["hits"] = rows
    yj.append(d)
    log("[yj] %-28s status=%s hits=%s" % (q, st, len(d.get("hits", []))))
    time.sleep(2)
res["yahoo_jp"] = yj

# ---------- 4. はてなブックマーク ----------
HB = ["withr", "withr17", "yunn", "案山子島", "ONE's MIDI"]
hb = []
for q in HB:
    url = "https://b.hatena.ne.jp/search/text?q=" + urllib.parse.quote(q) + "&sort=recent"
    st, txt = get(url)
    d = {"q": q, "status": st, "len": len(txt or ""), "url": url}
    if txt and st == 200:
        rows = re.findall(r'<a href="(https?://[^"]+)" class="entry-link"[^>]*>(.*?)</a>', txt, re.S)
        if not rows:
            rows = re.findall(r'<a href="(https?://[^"]+)"[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</a>', txt, re.S)
        d["hits"] = [{"url": u, "title": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t))[:120]}
                     for u, t in rows[:15]]
        if not d["hits"]:
            d["head"] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", txt))[:300]
    hb.append(d)
    log("[hb] %-12s status=%s hits=%s" % (q, st, len(d.get("hits", []))))
    time.sleep(1)
res["hatena"] = hb

# ---------- 5. Yahoo!リアルタイム検索 ----------
RT = ["withr", "案山子島", "withr17"]
rt = []
for q in RT:
    url = "https://search.yahoo.co.jp/realtime/search?p=" + urllib.parse.quote(q)
    st, txt = get(url)
    d = {"q": q, "status": st, "len": len(txt or "")}
    if txt and st == 200:
        d["head"] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", txt))[:300]
    rt.append(d)
    log("[rt] %-10s status=%s" % (q, st))
    time.sleep(1)
res["realtime"] = rt

# ---------- 6. find.5ch.net 原始 HTML ----------
f5 = {}
for q in ["withr", "yunn", "oneyunn", "withr17"]:
    url = "https://find.5ch.net/search?q=" + urllib.parse.quote(q)
    st, txt = get(url, save="find5ch_" + q + ".html")
    d = {"status": st, "len": len(txt or ""), "url": url}
    if txt and st == 200:
        # 服务端渲染时会有 read.cgi 链接
        th = re.findall(r'href="(https?://[^"]*read\.cgi/[^"]+)"[^>]*>(.*?)</a>', txt, re.S)
        d["threads"] = [{"url": u, "title": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()[:100]}
                        for u, t in th[:30]]
        d["n_threads"] = len(d["threads"])
        # 找接口线索
        apis = re.findall(r'(?:fetch|url)\s*[:(]\s*["\']([^"\']{5,120})["\']', txt)
        d["api_hints"] = sorted(set(a for a in apis if "search" in a or "api" in a))[:10]
    f5[q] = d
    log("[find5ch] %-10s status=%s threads=%s" % (q, st, d.get("n_threads")))
    time.sleep(1)
res["find5ch"] = f5

# ---------- 7. Google ----------
gg = []
for q in ['site:nicovideo.jp withr', '"music.geocities.jp/withr17"', 'site:5ch.net "With R"']:
    url = "https://www.google.com/search?q=" + urllib.parse.quote(q) + "&num=20&hl=ja"
    st, txt = get(url)
    d = {"q": q, "status": st, "len": len(txt or "")}
    if txt and st == 200:
        rows = re.findall(r'<a href="/url\?q=([^&"]+)[^"]*"[^>]*>(.*?)</a>', txt, re.S)
        d["hits"] = [{"url": urllib.parse.unquote(u),
                      "title": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t))[:100]}
                     for u, t in rows[:20]]
    gg.append(d)
    log("[gg] %-32s status=%s hits=%s" % (q, st, len(d.get("hits", []))))
    time.sleep(2)
res["google"] = gg

# ---------- 8. 知恵袋那条「素材サイト」问答 ----------
st, txt = get("https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q13150515323",
              save="chie_q13150515323.html")
d = {"status": st, "len": len(txt or "")}
if txt and st == 200:
    body = re.sub(r"<script.*?</script>", "", txt, flags=re.S)
    body = re.sub(r"<[^>]+>", "\n", body)
    body = re.sub(r"\n{2,}", "\n", body).strip()
    d["text"] = body[:2500]
res["chie_q13150515323"] = d
log("[chie-detail] status=%s len=%s" % (st, d["len"]))

json.dump(res, open(os.path.join(OUT, "jp2.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("DONE elapsed=%.0fs" % (time.time() - T0))
