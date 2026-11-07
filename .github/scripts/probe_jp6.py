#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日本论坛检索 第六轮：攻下ニコニコ大百科「ONE's」词条全文 + niconico 视频元数据

上一轮已从 Yahoo 摘要确认词条首段：
  「ONE's」とはかつて存在した個人サイトである。00年代前半から管理人のゆん氏により
  運営されていたMIDIサイト。オリジナル楽曲を専門としたサイトで、100点 …
但 dic.nicovideo.jp 对机房 IP 全封（CloudFront 403，Wayback 无存档）。

本轮走：
1. Google 翻译代理（translate.goog）——请求由 Google 发出，绕开 CloudFront
2. 大百科 API / 白板 / 手机版等其它路径
3. ext.nicovideo.jp/api/getthumbinfo —— 公开 XML 元数据（标题/投稿日/投稿者/播放数/简介）
4. Yahoo 侧补搜：把词条摘要按关键词切出来
"""
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request

OUT = "out_jp6"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp6.txt"), "w", encoding="utf-8")


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


def text_of(t, n=4000):
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

# ---------- 1. 大百科词条：多条替代通道 ----------
DIC = [
    ("tgoog_base", "https://dic-nicovideo-jp.translate.goog/a/one%27s?_x_tr_sl=ja&_x_tr_tl=zh-CN&_x_tr_hl=ja"),
    ("tgoog_nohdr", "https://dic-nicovideo-jp.translate.goog/a/one's?_x_tr_sl=auto&_x_tr_tl=en&_x_tr_hl=en"),
    ("api_article", "https://dic.nicovideo.jp/api/getarticle?title=one%27s"),
    ("whiteboard", "https://dic.nicovideo.jp/b/a/one%27s/"),
    ("mobile", "https://sp.dic.nicovideo.jp/a/one%27s"),
]
dic = {}
for tag, url in DIC:
    ST, TXT = get(url, save="dic6_%s.html" % tag)
    d = {"status": ST, "len": len(TXT or ""), "url": url}
    if TXT:
        d["text"] = text_of(TXT, 4000)
    dic[tag] = d
    log("[dic6] %-12s status=%s len=%s" % (tag, ST, d["len"]))
    time.sleep(2)
res["dic"] = dic

# ---------- 2. getthumbinfo ----------
thumbs = {}
for v in ["sm42741897", "nm10255152", "nm11669772"]:
    url = "https://ext.nicovideo.jp/api/getthumbinfo/" + v
    ST, TXT = get(url, save="thumb_%s.xml" % v)
    d = {"status": ST, "len": len(TXT or ""), "xml": (TXT or "")[:2500]}
    for tagx in ["title", "description", "user_nicoten", "first_retrieve",
                 "view_counter", "comment_num", "mylist_counter", "length",
                 "user_id", "thumbnail_url"]:
        m = re.search(r"<%s>(.*?)</%s>" % (tagx, tagx), TXT or "", re.S)
        if m:
            d[tagx] = re.sub(r"\s+", " ", m.group(1)).strip()[:600]
    thumbs[v] = d
    log("[thumb] %-12s status=%s title=%s" % (v, ST, str(d.get("title"))[:40]))
    time.sleep(1)
res["thumbinfo"] = thumbs

# ---------- 3. Yahoo 侧切词条摘要 ----------
YJ = [
    'site:dic.nicovideo.jp "ONE\'s" MIDI ゆん',
    '"ONE\'s" "かつて存在した個人サイト"',
    'site:dic.nicovideo.jp ゆん MIDI',
    'site:dic.nicovideo.jp withr',
    '"ONE\'s" "管理人" "ゆん" MIDI サイト 100',
    'site:nicovideo.jp "案山子島" "ゆん"',
]
yj = []
for q in YJ:
    url = ("https://search.yahoo.co.jp/search?p=" + urllib.parse.quote(q) + "&ei=UTF-8&n=30")
    ST, TXT = get(url, save="yj6_%d.html" % len(yj))
    d = {"q": q, "status": ST, "len": len(TXT or "")}
    if TXT and ST == 200:
        cnt = re.search(r"約([\d,]+)件", TXT)
        d["count"] = cnt.group(0) if cnt else None
        rows = []
        for m in re.finditer(r'<div class="sw-Card__title"><a href="(https?://[^"]+)"', TXT):
            u = m.group(1)
            seg = TXT[m.start():m.start() + 4000]
            ti = re.search(r"<h3[^>]*>(.*?)</h3>", seg, re.S)
            de = re.search(r'sw-Card__description[^>]*>(.*?)</p>', seg, re.S)
            if not de:
                # 退化：取 title 之后到下一个卡片之间的可见文本
                seg2 = re.sub(r"<script.*?</script>", "", seg, flags=re.S)
                seg2 = re.sub(r"<[^>]+>", "|", seg2)
                seg2 = re.sub(r"\|{2,}", "|", seg2)
                frag = seg2.split("|", 3)
                de_txt = frag[3][:400] if len(frag) > 3 else ""
            else:
                de_txt = re.sub(r"<[^>]+>", "", de.group(1))
            rows.append({"url": u,
                         "title": re.sub(r"<[^>]+>", "", ti.group(1)).strip()[:100] if ti else "",
                         "desc": de_txt.strip()[:400]})
        d["hits"] = rows[:20]
    yj.append(d)
    log("[yj6] %-40s status=%s %s n=%s" % (q, ST, d.get("count"), len(d.get("hits", []))))
    time.sleep(2)
res["yahoo"] = yj

json.dump(res, open(os.path.join(OUT, "jp6.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("DONE elapsed=%.0fs" % (time.time() - T0))
