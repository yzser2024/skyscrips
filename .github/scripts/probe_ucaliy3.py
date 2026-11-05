# -*- coding: utf-8 -*-
"""probe3: 修 add() 签名 + 补查 Twitter/Instagram/YouTube 的存档，
   并抓 withr17 menu 页老快照，定位「Follow ucaliy on Twitter」徽章最早出现的时点。
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_ua3"
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


def get(url, timeout=25, headers=None):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "ja,en;q=0.8"}
    if headers:
        h.update(headers)
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(600000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read(200000).decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return None, str(e)[:80]


def add(tag, url, status, body, extra=""):
    b = (body or "")[:300].replace("\n", " ")
    R.append({"tag": tag, "url": url, "status": status, "body": b, "extra": extra})
    note("%-20s %-5s %s" % (tag, status, (extra or b)[:110]))
    json.dump(R, open(OUT + "/probe3.json", "w"), ensure_ascii=False, indent=1)


# ---------- 1. HTML 判活 ----------
HTMLS = [
    ("Instagram", "https://www.instagram.com/ucaliy/",
     ["Sorry, this page", "isn't available", "Page Not Found"]),
    ("Pinterest", "https://www.pinterest.com/ucaliy/",
     ["couldn't find", "User not found", "ページが見つかりません"]),
    ("Threads", "https://www.threads.net/@ucaliy",
     ["Sorry, this page", "isn't available"]),
    ("Twitch", "https://www.twitch.tv/ucaliy",
     ["does not exist", "Sorry. Unless you"]),
    ("YouTube@", "https://www.youtube.com/@ucaliy",
     ["This channel does not exist", "not available"]),
]
for t, u, keys in HTMLS:
    st, b = get(u, timeout=28)
    hit = [k for k in keys if k.lower() in (b or "").lower()]
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', b or "", re.S)
    og = m.group(1) if m else ""
    ttl = ""
    mt = re.search(r"<title[^>]*>(.*?)</title>", b or "", re.S | re.I)
    if mt:
        ttl = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", mt.group(1))).strip()[:90]
    add(t, u, st, b, "og=%s | title=%s | hits=%s | len=%d" % (og[:60], ttl, hit, len(b or "")))
    time.sleep(1)

# ---------- 2. CDX ----------
def cdx(prefix, tag, limit=1500, filt="statuscode:200"):
    q = ("http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(prefix, safe="")
         + "&matchType=prefix&output=json&fl=timestamp,original,statuscode&limit=%d" % limit)
    if filt:
        q += "&filter=" + filt
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
    note("[cdx] %-14s status=%s rows=%d" % (tag, st, len(rows)))
    if rows:
        note("       %s → %s" % (rows[0]["timestamp"], rows[-1]["timestamp"]))
    return rows


cdx("twitter.com/ucaliy", "tw")
cdx("instagram.com/ucaliy", "ig")
cdx("youtube.com/@ucaliy", "yt", filt=None)
cdx("music.geocities.jp/withr17/menu.html", "menu")

# ---------- 3. 抓 menu 老快照，找徽章首次出现 ----------
men = json.load(open(OUT + "/cdx_menu.json"))["rows"]
ts = sorted(set(r["timestamp"][:8] for r in men))
note("menu 快照日期 %d 个: %s" % (len(ts), ts[:40]))
picks = []
if ts:
    picks = [ts[0], ts[len(ts) // 3], ts[len(ts) // 2], ts[2 * len(ts) // 3], ts[-1]]
picks = sorted(set(picks))
for d in picks:
    u = "http://web.archive.org/web/%s110000/http://music.geocities.jp/withr17/menu.html" % d
    st, b = get(u, timeout=40)
    low = (b or "").lower()
    add("menu@%s" % d, u, st, b,
        "ucaliy=%s | twitter=%s | len=%d" % ("ucaliy" in low, "twitter" in low, len(b or "")))
    time.sleep(1)

note("DONE")
