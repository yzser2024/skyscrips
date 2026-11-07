#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日本论坛检索 第三轮：顺着第二轮唯一的新线索（note 上提到 ONE's 的文章）往里走，
并把 Yahoo! JAPAN（唯一稳定出结果的日文搜索）用足。

1. note.com/tristeza417 那篇 + 该作者的文章列表
2. Yahoo! JAPAN 多组关键词（含 site: 限定）
3. niconico 视频页完整数据 + 投稿者 はにはに 的投稿列表
4. niconico 搜索页 / 标签页（浏览器 UA）
5. したらば・おーぷん2ch 用 site: 反查
"""
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request

OUT = "out_jp3"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp3.txt"), "w", encoding="utf-8")


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


def get(url, headers=None, timeout=30, save=None):
    if time.time() - T0 > BUDGET:
        return "SKIP", ""
    h = {"User-Agent": UA, "Accept-Language": "ja,en;q=0.8",
         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
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


def text_of(t, n=1200):
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()[:n]


res = {}

# ---------- 1. note 文章 ----------
notes = {}
ST, TXT = get("https://note.com/tristeza417/n/n14c4601353c0", save="note_n14c.html")
d = {"status": ST, "len": len(TXT or "")}
if TXT and ST == 200:
    m = re.search(r"<title>([^<]+)</title>", TXT)
    d["title"] = m.group(1).strip() if m else ""
    j = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', TXT, re.S)
    if j:
        try:
            nd = json.loads(j.group(1))
            s = json.dumps(nd, ensure_ascii=False)
            # 抽正文
            mm = re.search(r'"body":"(.*?)","', s)
            d["body_len"] = len(s)
            for m2 in re.finditer(r'"name":"([^"]{1,40})","body":"(.{50,4000}?)"', s):
                d.setdefault("bodies", []).append(m2.group(2)[:3000])
        except Exception as e:
            d["next_err"] = str(e)
    d["text"] = text_of(TXT, 3000)
notes["n14c4601353c0"] = d
log("[note] status=%s title=%s" % (ST, d.get("title", "")[:60]))

# 作者主页与文章列表
ST2, TXT2 = get("https://note.com/tristeza417", save="note_user.html")
d2 = {"status": ST2, "len": len(TXT2 or "")}
if TXT2 and ST2 == 200:
    arts = re.findall(r'href="(/tristeza417/n/[a-z0-9]+)"[^>]*>(.{0,120}?)</a>', TXT2, re.S)
    seen, rows = set(), []
    for u, t in arts:
        if u in seen:
            continue
        seen.add(u)
        rows.append({"url": "https://note.com" + u,
                     "title": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()[:100]})
    d2["articles"] = rows
    d2["text"] = text_of(TXT2, 800)
notes["user_tristeza417"] = d2
log("[note-user] status=%s articles=%s" % (ST2, len(d2.get("articles", []))))
res["note"] = notes

# ---------- 2. Yahoo! JAPAN ----------
YJ = [
    '"ONE\'s" MIDI サイト 閉鎖',
    'site:note.com ONE\'s MIDI',
    '"MIDI楽曲サイト"',
    '"withr17"',
    'withr ニコニコ',
    '"案山子島" ニコニコ',
    '"曇一" 歌ってみた',
    'site:5ch.net "MIDIサイト"',
    'site:dic.nicovideo.jp "MIDI"',
    'site:shitaraba.net withr',
    'site:2ch.sc withr',
    '"With R" 別館 ピアノ rico',
]
yj = []
for q in YJ:
    url = ("https://search.yahoo.co.jp/search?p=" + urllib.parse.quote(q)
           + "&ei=UTF-8&n=30")
    tag = "yj3_%d.html" % (len(yj))
    ST, TXT = get(url, save=tag)
    d = {"q": q, "status": ST, "len": len(TXT or "")}
    if TXT and ST == 200:
        cnt = re.search(r"約([\d,]+)件", TXT)
        d["count"] = cnt.group(0) if cnt else None
        blocks = re.findall(
            r'<a href="(https?://[^"]+)" class="sw-Card__titleInner".*?<h3[^>]*>(?:<span>(.*?)</span>)?</h3>',
            TXT, re.S)
        rows = []
        for u, ti in blocks:
            ti = re.sub(r"<[^>]+>", "", ti or "").strip()
            rows.append({"url": u, "title": ti[:120]})
        d["hits"] = rows[:20]
    yj.append(d)
    log("[yj3] %-32s status=%s %s n=%s" % (q, ST, d.get("count"), len(d.get("hits", []))))
    time.sleep(2)
res["yahoo"] = yj

# ---------- 3. niconico 视频与投稿者 ----------
vids = {}
for v in ["nm10255152", "nm11669772"]:
    ST, TXT = get("https://www.nicovideo.jp/watch/" + v, save="nico_%s.html" % v)
    d = {"status": ST, "len": len(TXT or "")}
    if TXT and ST == 200:
        j = re.search(r'<meta name="server-response" content="(.*?)"', TXT, re.S)
        if j:
            import html as H
            try:
                sd = json.loads(H.unescape(j.group(1)))
                d["server_response"] = "ok"
                json.dump(sd, open(os.path.join(OUT, "sr_%s.json" % v), "w"),
                          ensure_ascii=False, indent=1)
            except Exception as e:
                d["sr_err"] = str(e)
        for pat, key in [(r'"title":"(.{1,120}?)"', "title"),
                         (r'"description":"(.{0,600}?)","', "desc"),
                         (r'"registeredAt":"([^"]+)"', "registered"),
                         (r'"userId":(\d+)', "userId"),
                         (r'"viewCount":(\d+)', "views")]:
            m = re.search(pat, TXT)
            if m:
                d[key] = m.group(1)
    vids[v] = d
    log("[vid3] %-12s status=%s user=%s views=%s" % (v, ST, d.get("userId"), d.get("views")))
    time.sleep(1)

# 投稿者页面
uid = vids.get("nm10255152", {}).get("userId")
if uid:
    ST, TXT = get("https://www.nicovideo.jp/user/%s/video" % uid, save="nico_user_%s.html" % uid)
    d = {"status": ST, "len": len(TXT or ""), "uid": uid}
    if TXT and ST == 200:
        titles = re.findall(r'"title":"(.{1,120}?)","', TXT)
        d["titles"] = titles[:40]
        d["n"] = len(titles)
    vids["user_" + uid] = d
    log("[user] %s status=%s titles=%s" % (uid, ST, len(d.get("titles", []))))
res["videos"] = vids

# ---------- 4. niconico 搜索页 / 标签页 ----------
ns = {}
for path in ["/search/withr", "/search/%E6%A1%88%E5%B1%B1%E5%AD%90%E5%B3%B6", "/tag/withr",
             "/search/withr17"]:
    ST, TXT = get("https://www.nicovideo.jp" + path, save="nicos_" + path.replace("/", "_")[:30] + ".html")
    d = {"status": ST, "len": len(TXT or "")}
    if TXT and ST == 200:
        items = re.findall(r'"title":"(.{1,120}?)","', TXT)
        d["titles"] = list(dict.fromkeys(items))[:20]
        d["n"] = len(d["titles"])
    ns[path] = d
    log("[nicos] %-30s status=%s n=%s" % (path, ST, d.get("n")))
    time.sleep(1)
res["nico_search_pages"] = ns

json.dump(res, open(os.path.join(OUT, "jp3.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("DONE elapsed=%.0fs" % (time.time() - T0))
