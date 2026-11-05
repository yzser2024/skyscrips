# -*- coding: utf-8 -*-
"""probe2: 把第一轮里「200 但只是空壳」的平台逐个核实。
手段：oEmbed / 公开 API / Wayback availability + CDX。
输出 out_ua2/
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_ua2"
os.makedirs(OUT, exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
R = []


def note(s):
    line = "%s %s" % (time.strftime("%H:%M:%S"), s)
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()


def get(url, timeout=22, headers=None):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "ja,en;q=0.8"}
    if headers:
        h.update(headers)
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(500000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read(200000).decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return None, str(e)[:80]


def add(tag, url, status, body, note_=""):
    b = (body or "")[:400].replace("\n", " ")
    R.append({"tag": tag, "url": url, "status": status, "body": b, "note": note_})
    note("%-22s %-5s %s" % (tag, status, note_ or b[:110]))
    json.dump(R, open(OUT + "/probe2.json", "w"), ensure_ascii=False, indent=1)


# ---------- oEmbed / API：返回 JSON 即真实存在 ----------
OEMB = [
    ("oEmbed YouTube@", "https://www.youtube.com/oembed?url=https://www.youtube.com/@ucaliy&format=json"),
    ("oEmbed YouTube/user", "https://www.youtube.com/oembed?url=https://www.youtube.com/user/ucaliy&format=json"),
    ("oEmbed TikTok", "https://www.tiktok.com/oembed?url=https://www.tiktok.com/@ucaliy"),
    ("oEmbed Twitter", "https://publish.twitter.com/oembed?url=https://twitter.com/ucaliy"),
    ("oEmbed SoundCloud", "https://soundcloud.com/oembed?url=https://soundcloud.com/ucaliy&format=json"),
    ("WP public API", "https://public-api.wordpress.com/rest/v1.1/sites/ucaliy.wordpress.com"),
    ("WP public API2", "https://public-api.wordpress.com/rest/v1.1/sites/ucaliy.wordpress.com/posts/?number=1"),
]
for t, u in OEMB:
    st, b = get(u)
    add(t, u, st, b)
    time.sleep(0.6)

# ---------- HTML 判活：抓关键字 ----------
HTMLS = [
    ("Instagram HTML", "https://www.instagram.com/ucaliy/",
     ["Sorry, this page", "isn't available", "Page Not Found", "page not found"]),
    ("Pinterest HTML", "https://www.pinterest.com/ucaliy/",
     ["couldn't find", "not found", "User not found", "ページが見つかりません"]),
    ("Threads HTML", "https://www.threads.net/@ucaliy",
     ["Sorry, this page", "isn't available", "not found"]),
    ("Twitch HTML", "https://www.twitch.tv/ucaliy",
     ["does not exist", "not found", "Sorry. Unless you"]),
    ("YouTube @ HTML", "https://www.youtube.com/@ucaliy",
     ["This channel does not exist", "not available", "404"]),
]
for t, u, keys in HTMLS:
    st, b = get(u, timeout=25)
    hit = [k for k in keys if k.lower() in (b or "").lower()]
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', b or "", re.S)
    og = m.group(1) if m else ""
    add(t, u, st, b, note="og:title=%s | hits=%s | len=%d" % (og[:70], hit, len(b or "")))
    time.sleep(0.8)

# ---------- Wayback availability ----------
def avail(u, tag):
    q = "https://archive.org/wayback/available?url=" + urllib.parse.quote(u, safe="")
    st, b = get(q, timeout=30)
    try:
        d = json.loads(b)
    except Exception:
        d = {"_raw": (b or "")[:200]}
    snap = (d.get("archived_snapshots") or {}).get("closest") or {}
    add(tag, q, st, json.dumps(d, ensure_ascii=False)[:380],
        note="snap=%s %s" % (snap.get("timestamp"), snap.get("url")))


for t, u in [("avail twitter", "twitter.com/ucaliy"),
             ("avail x", "x.com/ucaliy"),
             ("avail instagram", "instagram.com/ucaliy"),
             ("avail youtube@", "youtube.com/@ucaliy"),
             ("avail pinterest", "pinterest.com/ucaliy"),
             ("avail wordpress", "ucaliy.wordpress.com"),
             ("avail tumblr", "ucaliy.tumblr.com")]:
    avail(u, t)
    time.sleep(1)

# ---------- CDX：每个平台前缀一次 ----------
def cdx(prefix, tag, limit=800):
    q = ("http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(prefix, safe="")
         + "&matchType=prefix&output=json&fl=timestamp,original,statuscode"
         "&filter=statuscode:200&limit=%d" % limit)
    st, b = get(q, timeout=55)
    rows = []
    if b and b.strip().startswith("["):
        try:
            d = json.loads(b)
            if d and isinstance(d[0], list):
                rows = [dict(zip(d[0], r)) for r in d[1:]]
        except Exception as e:
            note("cdx parse fail %s" % e)
    json.dump({"tag": tag, "status": st, "count": len(rows), "rows": rows},
              open(OUT + "/cdx_%s.json" % tag, "w"), ensure_ascii=False)
    note("[cdx] %-12s status=%s rows=%d" % (tag, st, len(rows)))
    if rows:
        note("       first=%s %s" % (rows[0]["timestamp"], rows[0]["original"][:70]))
        note("       last =%s %s" % (rows[-1]["timestamp"], rows[-1]["original"][:70]))
    return rows


for p, t in [("twitter.com/ucaliy", "tw"),
             ("instagram.com/ucaliy", "ig"),
             ("youtube.com/@ucaliy", "yt"),
             ("pinterest.com/ucaliy", "pin")]:
    cdx(p, t)
    time.sleep(1)

note("DONE")
