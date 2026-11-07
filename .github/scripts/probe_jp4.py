#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日本论坛检索 第四轮：核实第三轮冒出来的四个新点

A. ニコニコ大百科「ONE's」词条（dic 直连 403，走 Wayback）
B. niconico 视频 sm42741897「【ONE's】案山子島【ゆん】」+ 标签页 one's
C. はてなアンテナ Carnegie1（日本老牌网页监视服务）里与 withr 相关的记录
D. note 作者 TRISTEZA 的自站 tristeza.web.fc2.com
E. 补充 Yahoo 查询（site:dic、site:nicovideo、大百科词条名）
"""
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request

OUT = "out_jp4"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp4.txt"), "w", encoding="utf-8")


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
BUDGET = 1100


def get(url, headers=None, timeout=35, save=None):
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


def text_of(t, n=1500):
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = (t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
          .replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">"))
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()[:n]


res = {}

# ---------- A. 大百科「ONE's」词条：直连 + Wayback ----------
dic = {}
for tag, url in [
    ("direct", "https://dic.nicovideo.jp/a/one%27s"),
    ("wb_index", "https://web.archive.org/cdx/search/cdx?url=dic.nicovideo.jp/a/one*&output=json&limit=40&collapse=urlkey"),
    ("wb_page", "https://web.archive.org/web/2024/https://dic.nicovideo.jp/a/one%27s"),
    ("wb_page2", "https://web.archive.org/web/2020/https://dic.nicovideo.jp/a/one%27s"),
]:
    ST, TXT = get(url, save="dic_%s.html" % tag)
    d = {"status": ST, "len": len(TXT or ""), "url": url}
    if TXT and ST in (200, 302):
        d["text"] = text_of(TXT, 1800)
    dic[tag] = d
    log("[dic4] %-10s status=%s len=%s" % (tag, ST, d["len"]))
    time.sleep(1)
res["dic_ones"] = dic

# ---------- B. niconico 视频 sm42741897 与标签页 ----------
nico = {}
for tag, url in [
    ("sm42741897", "https://www.nicovideo.jp/watch/sm42741897"),
    ("tag_ones", "https://www.nicovideo.jp/tag/one%27s"),
    ("tag_ones2", "https://www.nicovideo.jp/tag/ONE%27s"),
]:
    ST, TXT = get(url, save="nico4_%s.html" % tag)
    d = {"status": ST, "len": len(TXT or ""), "url": url}
    if TXT and ST == 200:
        d["text"] = text_of(TXT, 1400)
        for pat, key in [(r'"title":"(.{1,120}?)"', "title"),
                         (r'"description":"(.{0,500}?)","', "desc"),
                         (r'"registeredAt":"([^"]+)"', "registeredAt"),
                         (r'"viewCount":(\d+)', "views"),
                         (r'"commentCount":(\d+)', "comments"),
                         (r'"userId":(\d+)', "userId")]:
            m = re.search(pat, TXT)
            if m:
                d[key] = m.group(1)
        d["all_titles"] = list(dict.fromkeys(re.findall(r'"title":"(.{1,90}?)"', TXT)))[:25]
    nico[tag] = d
    log("[nico4] %-12s status=%s title=%s" % (tag, ST, str(d.get("title"))[:50]))
    time.sleep(1)
res["nico4"] = nico

# ---------- C. はてなアンテナ ----------
hat = {}
for tag, url in [
    ("carnegie1", "https://a.hatena.ne.jp/Carnegie1/"),
    ("carnegie1_of400", "https://a.hatena.ne.jp/Carnegie1/?of=400"),
]:
    ST, TXT = get(url, save="hatena_%s.html" % tag)
    d = {"status": ST, "len": len(TXT or ""), "url": url}
    if TXT and ST == 200:
        items = re.findall(r'href="(https?://[^"]+)"[^>]*>(.{0,100}?)</a>', TXT, re.S)
        rows = []
        for u, t in items:
            t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()
            if any(k in (u + t).lower() for k in ["withr", "one's", "ones", "ゆん", "ribbon", "geocities"]):
                rows.append({"url": u, "title": t[:100]})
        d["matched"] = rows
        d["n_links"] = len(items)
        if not rows:
            d["text"] = text_of(TXT, 600)
    hat[tag] = d
    log("[hatena] %-14s status=%s links=%s matched=%s" % (tag, ST, d.get("n_links"), len(d.get("matched", []))))
    time.sleep(1)
res["hatena_antenna"] = hat

# ---------- D. TRISTEZA 自站 ----------
tri = {}
for tag, url in [
    ("top", "http://tristeza.web.fc2.com/"),
    ("link", "http://tristeza.web.fc2.com/link.html"),
    ("old", "http://tristeza.web.fc2.com/old.html"),
]:
    ST, TXT = get(url, save="tristeza_%s.html" % tag)
    d = {"status": ST, "len": len(TXT or ""), "url": url}
    if TXT and ST == 200:
        d["text"] = text_of(TXT, 1200)
        d["links"] = list(dict.fromkeys(re.findall(r'href="([^"]+)"', TXT)))[:40]
    tri[tag] = d
    log("[tristeza] %-6s status=%s len=%s" % (tag, ST, d["len"]))
    time.sleep(1)
res["tristeza"] = tri

# ---------- E. Yahoo 补充 ----------
YJ = [
    'site:dic.nicovideo.jp "ONE\'s"',
    'site:nicovideo.jp "ONE\'s"',
    '"ONE\'s" ワンズ ニコニコ大百科',
    'sm42741897',
    'site:nicovideo.jp "withr"',
    '"案山子島" "ゆん"',
    '"ONE\'s" "ゆん" "rico"',
    'site:a.hatena.ne.jp withr',
]
yj = []
for q in YJ:
    url = ("https://search.yahoo.co.jp/search?p=" + urllib.parse.quote(q) + "&ei=UTF-8&n=30")
    ST, TXT = get(url, save="yj4_%d.html" % len(yj))
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
    log("[yj4] %-34s status=%s %s n=%s" % (q, ST, d.get("count"), len(d.get("hits", []))))
    time.sleep(2)
res["yahoo"] = yj

json.dump(res, open(os.path.join(OUT, "jp4.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("DONE elapsed=%.0fs" % (time.time() - T0))
