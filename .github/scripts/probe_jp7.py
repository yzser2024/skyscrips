#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日本论坛检索 第七轮

已确认两条硬线索，本轮把它们补全：
A. niconico 上 2023-09 有人用 SC-88Pro「再現」她的 MIDI，标题格式【ONE's】曲名【ゆん】
   —— 用标签 RSS / 搜索 RSS 把整个系列列全
B. ニコニコ大百科「ONE's」词条：已拿到前三句，用不同关键词把后段切出来
C. 顺带确认 tag/one's 的 96 本里还有哪些是她
"""
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request

OUT = "out_jp7"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp7.txt"), "w", encoding="utf-8")


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
BUDGET = 900


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


res = {}

# ---------- A. niconico RSS ----------
rss = {}
RSS = [
    ("tag_ones", "https://www.nicovideo.jp/tag/one%27s?rss=2.0"),
    ("search_ones", "https://www.nicovideo.jp/search/ONE%27s?rss=2.0"),
    ("search_yun", "https://www.nicovideo.jp/search/%E3%82%86%E3%82%93?rss=2.0"),
    ("tag_yun", "https://www.nicovideo.jp/tag/%E3%82%86%E3%82%93?rss=2.0"),
]
for tag, url in RSS:
    ST, TXT = get(url, save="rss_%s.xml" % tag)
    d = {"status": ST, "len": len(TXT or "")}
    if TXT:
        items = re.findall(r"<item>(.*?)</item>", TXT, re.S)
        rows = []
        for it in items:
            t = re.search(r"<title>(.*?)</title>", it, re.S)
            l = re.search(r"<link>(.*?)</link>", it, re.S)
            p = re.search(r"<pubDate>(.*?)</pubDate>", it, re.S)
            de = re.search(r"<description>(.*?)</description>", it, re.S)
            rows.append({"title": (t.group(1) if t else "").strip()[:100],
                         "link": (l.group(1) if l else "").strip(),
                         "date": (p.group(1) if p else "").strip(),
                         "desc": (de.group(1) if de else "").strip()[:200]})
        d["items"] = rows
        d["n"] = len(rows)
        d["ones_like"] = [r for r in rows if "ONE" in r["title"] or "ゆん" in r["title"]]
    rss[tag] = d
    log("[rss] %-12s status=%s items=%s ones=%s"
        % (tag, ST, d.get("n"), len(d.get("ones_like", []))))
    time.sleep(1)
res["rss"] = rss

# ---------- B. 大百科词条后段（Yahoo 切词） ----------
YJ = [
    'site:dic.nicovideo.jp "ONE\'s" "姉妹サイト"',
    '"ONE\'s" "2010年頃にサーバー"',
    '"ONE\'s" "With R" "rico" ヴォーカル',
    '"ONE\'s" "案山子島" "blueland"',
    'site:nicovideo.jp "【ONE\'s】"',
    '"【ONE\'s】" "ゆん" ニコニコ',
]
yj = []
for q in YJ:
    url = ("https://search.yahoo.co.jp/search?p=" + urllib.parse.quote(q) + "&ei=UTF-8&n=30")
    ST, TXT = get(url, save="yj7_%d.html" % len(yj))
    d = {"q": q, "status": ST, "len": len(TXT or "")}
    if TXT and ST == 200:
        cnt = re.search(r"約([\d,]+)件", TXT)
        d["count"] = cnt.group(0) if cnt else None
        rows = []
        for m in re.finditer(r'<div class="sw-Card__title"><a href="(https?://[^"]+)"', TXT):
            u = m.group(1)
            seg = TXT[m.start():m.start() + 4000]
            ti = re.search(r"<h3[^>]*>(.*?)</h3>", seg, re.S)
            seg2 = re.sub(r"<script.*?</script>", "", seg, flags=re.S)
            seg2 = re.sub(r"<[^>]+>", "|", seg2)
            seg2 = re.sub(r"\|{2,}", "|", seg2)
            rows.append({"url": u,
                         "title": re.sub(r"<[^>]+>", "", ti.group(1)).strip()[:100] if ti else "",
                         "desc": seg2[:500]})
        d["hits"] = rows[:20]
    yj.append(d)
    log("[yj7] %-42s status=%s %s n=%s" % (q, ST, d.get("count"), len(d.get("hits", []))))
    time.sleep(2)
res["yahoo"] = yj

json.dump(res, open(os.path.join(OUT, "jp7.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("DONE elapsed=%.0fs" % (time.time() - T0))
