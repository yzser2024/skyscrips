# -*- coding: utf-8 -*-
"""tl-1: 时间线证据补抓
A. Wayback CDX 全量快照时间轴（6 个站 + soundcloud + tumblr）
B. SoundCloud: user / followings / likes / reposts / tracks / 本人评论 / 每曲评论
C. Tumblr: 旧 api/read/json，失败退 rss
输出 out_tl/*.json，最后打 zip。
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_tl"
os.makedirs(OUT, exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True)
    LOG.write(str(s) + "\n")
    LOG.flush()


def get(url, tries=4, timeout=60, raw=False):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "*/*",
                "Accept-Language": "ja,en;q=0.8"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                return r.status, (b if raw else b.decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            last = "HTTP %d" % e.code
            note("    %s %s" % (last, url[:110]))
            if e.code in (429, 503):
                time.sleep(45 + i * 30)
            elif e.code == 404:
                return 404, b"" if raw else ""
            else:
                time.sleep(4 + i * 6)
        except Exception as e:
            last = str(e)[:80]
            note("    ERR %s %s" % (last, url[:110]))
            time.sleep(4 + i * 6)
    return None, (b"" if raw else "")


# ---------- A. CDX ----------
SITES = [
    ("withr17_geocities", "music.geocities.jp/withr17/"),
    ("withr79_geocities", "www.geocities.jp/withr79/"),
    ("oneyunn79_geocities", "www.geocities.jp/oneyunn79/"),
    ("oneyunn79_client", "oneyunn79.client.jp/"),
    ("amorxxx79_geocities", "www.geocities.jp/amorxxx79/"),
    ("ribbon_withr", "withr.y.ribbon.to/"),
    ("yellow_ribbon", "yellow.ribbon.to/~withr/"),
    ("soundcloud_withr", "soundcloud.com/withr"),
    ("tumblr_ucaliy", "ucaliy.tumblr.com/"),
    ("rocketbbs_610", "www1.rocketbbs.com/610/withr.html"),
]

cdx_all = {}
for name, target in SITES:
    q = ("http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(target, safe="")
         + "&matchType=prefix&output=json&fl=timestamp,original,statuscode,digest,length"
         + "&limit=30000")
    note("[cdx] %s %s" % (name, target))
    st, body = get(q, tries=5, timeout=180)
    rows = []
    if body and body.strip().startswith("["):
        try:
            data = json.loads(body)
            if data and isinstance(data[0], list):
                head = data[0]
                rows = [dict(zip(head, r)) for r in data[1:]]
        except Exception as e:
            note("    parse fail %s" % e)
    note("    -> %d rows (status %s)" % (len(rows), st))
    cdx_all[name] = {"target": target, "count": len(rows), "rows": rows}
    json.dump(cdx_all[name], open(OUT + "/cdx_%s.json" % name, "w"),
              ensure_ascii=False, indent=1)
    time.sleep(6)

json.dump({k: v["count"] for k, v in cdx_all.items()},
          open(OUT + "/cdx_counts.json", "w"), ensure_ascii=False, indent=1)

# ---------- B. SoundCloud ----------
SC = {}
st, home = get("https://soundcloud.com/withr")
open(OUT + "/sc_home.html", "w", encoding="utf-8").write(home or "")
cid = None
try:
    m = re.search(r'window\.__sc_hydration\s*=\s*(\[.*?\]);', home or "", re.S)
    hyd = json.loads(m.group(1))
    for x in hyd:
        if x.get("hydratable") == "apiClient":
            cid = x["data"].get("id")
        if x.get("hydratable") == "user":
            SC["hydration_user"] = x["data"]
except Exception as e:
    note("hydration fail %s" % e)
note("client_id=%s" % cid)
SC["client_id"] = cid

API = "https://api-v2.soundcloud.com"
uid = 123211690
if cid:
    eps = {
        "user": "%s/users/%d?client_id=%s" % (API, uid, cid),
        "followings": "%s/users/%d/followings?limit=100&client_id=%s" % (API, uid, cid),
        "followers": "%s/users/%d/followers?limit=200&client_id=%s" % (API, uid, cid),
        "likes": "%s/users/%d/likes?limit=200&client_id=%s" % (API, uid, cid),
        "reposts": "%s/stream/users/%d/reposts?limit=200&client_id=%s" % (API, uid, cid),
        "mycomments": "%s/users/%d/comments?limit=200&client_id=%s" % (API, uid, cid),
        "tracks": "%s/users/%d/tracks?limit=200&client_id=%s" % (API, uid, cid),
        "playlists": "%s/users/%d/playlists?limit=100&client_id=%s" % (API, uid, cid),
    }
    for k, u in eps.items():
        st, b = get(u)
        note("[sc] %s -> %s %d bytes" % (k, st, len(b or "")))
        try:
            SC[k] = json.loads(b)
        except Exception:
            SC[k] = {"_raw": (b or "")[:2000], "_status": st}
        time.sleep(2)

# 每首曲的评论（含老听众 2019 留言的精确时间）
tr = SC.get("tracks")
lst = tr.get("collection") if isinstance(tr, dict) else None
SC["track_comments"] = {}
for t in (lst or []):
    tid = t.get("id")
    u = "%s/tracks/%d/comments?limit=200&client_id=%s" % (API, tid, cid)
    st, b = get(u)
    try:
        SC["track_comments"][str(tid)] = json.loads(b)
    except Exception:
        SC["track_comments"][str(tid)] = {"_status": st}
    note("    comments %s (%s) -> %s" % (t.get("title"), tid, st))
    time.sleep(1.5)

json.dump(SC, open(OUT + "/soundcloud.json", "w"), ensure_ascii=False, indent=1)

# ---------- C. Tumblr ----------
TB = {}
for name, u in [
    ("api_read_json_0", "https://ucaliy.tumblr.com/api/read/json?num=50&start=0"),
    ("api_read_json_50", "https://ucaliy.tumblr.com/api/read/json?num=50&start=50"),
    ("rss", "https://ucaliy.tumblr.com/rss"),
    ("archive", "https://ucaliy.tumblr.com/archive"),
]:
    st, b = get(u, timeout=90)
    note("[tb] %s -> %s %d bytes" % (name, st, len(b or "")))
    TB[name] = {"status": st, "body": (b or "")[:400000]}
    time.sleep(2)
json.dump(TB, open(OUT + "/tumblr.json", "w"), ensure_ascii=False, indent=1)

note("DONE")
