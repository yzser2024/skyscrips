# -*- coding: utf-8 -*-
"""tl-2: 时间线证据补抓（轻量版）
1) SoundCloud 全量（user/followings/likes/reposts/tracks/评论）
2) Tumblr 旧接口
3) Wayback CDX：每站限量 + 只取 200 + collapse=digest，逐站落盘，单站失败不拖累
所有输出写 out_tl/，每步立即 flush 日志。
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
    line = "%s %s" % (time.strftime("%H:%M:%S"), s)
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()


def get(url, tries=3, timeout=45, raw=False):
    for i in range(tries):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "*/*",
                "Accept-Language": "ja,en;q=0.8"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                note("    ok %d bytes %.1fs" % (len(b), time.time() - t0))
                return r.status, (b if raw else b.decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            note("    HTTP %d %.1fs" % (e.code, time.time() - t0))
            if e.code == 404:
                return 404, (b"" if raw else "")
            time.sleep(5 + i * 8)
        except Exception as e:
            note("    ERR %s %.1fs" % (str(e)[:60], time.time() - t0))
            time.sleep(5 + i * 8)
    return None, (b"" if raw else "")


# ================= 1. SoundCloud =================
SC = {}
note("[sc] home")
st, home = get("https://soundcloud.com/withr", timeout=60)
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
    eps = [
        ("user", "%s/users/%d?client_id=%s" % (API, uid, cid)),
        ("followings", "%s/users/%d/followings?limit=100&client_id=%s" % (API, uid, cid)),
        ("likes", "%s/users/%d/likes?limit=200&client_id=%s" % (API, uid, cid)),
        ("reposts", "%s/stream/users/%d/reposts?limit=200&client_id=%s" % (API, uid, cid)),
        ("mycomments", "%s/users/%d/comments?limit=200&client_id=%s" % (API, uid, cid)),
        ("tracks", "%s/users/%d/tracks?limit=200&client_id=%s" % (API, uid, cid)),
        ("playlists", "%s/users/%d/playlists?limit=100&client_id=%s" % (API, uid, cid)),
    ]
    for k, u in eps:
        note("[sc] %s" % k)
        st, b = get(u)
        try:
            SC[k] = json.loads(b)
        except Exception:
            SC[k] = {"_raw": (b or "")[:3000], "_status": st}
        time.sleep(1.5)

    tr = SC.get("tracks")
    lst = tr.get("collection") if isinstance(tr, dict) else None
    SC["track_comments"] = {}
    for t in (lst or []):
        tid = t.get("id")
        note("[sc] comments of %s" % t.get("title"))
        st, b = get("%s/tracks/%d/comments?limit=200&client_id=%s" % (API, tid, cid))
        try:
            SC["track_comments"][str(tid)] = json.loads(b)
        except Exception:
            SC["track_comments"][str(tid)] = {"_status": st}
        time.sleep(1)

json.dump(SC, open(OUT + "/soundcloud.json", "w"), ensure_ascii=False, indent=1)
note("[sc] saved")

# ================= 2. Tumblr =================
TB = {}
for name, u in [
    ("api_read_json_0", "https://ucaliy.tumblr.com/api/read/json?num=50&start=0"),
    ("api_read_json_50", "https://ucaliy.tumblr.com/api/read/json?num=50&start=50"),
    ("rss", "https://ucaliy.tumblr.com/rss"),
]:
    note("[tb] %s" % name)
    st, b = get(u, timeout=60)
    TB[name] = {"status": st, "body": (b or "")[:500000]}
    time.sleep(1.5)
json.dump(TB, open(OUT + "/tumblr.json", "w"), ensure_ascii=False, indent=1)

# ================= 3. CDX =================
SITES = [
    ("withr17_geocities", "music.geocities.jp/withr17/"),
    ("withr79_geocities", "www.geocities.jp/withr79/"),
    ("oneyunn79_geocities", "www.geocities.jp/oneyunn79/"),
    ("amorxxx79_geocities", "www.geocities.jp/amorxxx79/"),
    ("ribbon_withr", "withr.y.ribbon.to/"),
    ("soundcloud_withr", "soundcloud.com/withr"),
    ("tumblr_ucaliy", "ucaliy.tumblr.com/"),
    ("rocketbbs_610", "www1.rocketbbs.com/610/withr.html"),
]
counts = {}
for name, target in SITES:
    q = ("http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(target, safe="")
         + "&matchType=prefix&output=json&fl=timestamp,original,statuscode,digest,length"
         + "&filter=statuscode:200&limit=5000")
    note("[cdx] %s" % name)
    st, body = get(q, tries=2, timeout=120)
    rows = []
    if body and body.strip().startswith("["):
        try:
            data = json.loads(body)
            if data and isinstance(data[0], list):
                head = data[0]
                rows = [dict(zip(head, r)) for r in data[1:]]
        except Exception as e:
            note("    parse fail %s" % e)
    counts[name] = len(rows)
    note("    rows=%d" % len(rows))
    json.dump({"target": target, "count": len(rows), "rows": rows},
              open(OUT + "/cdx_%s.json" % name, "w"), ensure_ascii=False)
    time.sleep(3)

json.dump(counts, open(OUT + "/cdx_counts.json", "w"), ensure_ascii=False, indent=1)
note("DONE")
