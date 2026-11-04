# -*- coding: utf-8 -*-
"""tl-3: 只抓 SoundCloud（+Tumblr + 一个 CDX）。
CDX 只留 soundcloud 一个站，单次 30 秒超时，失败即放弃，不重试。
每一步落盘并 flush，确保中途被杀也有文件。
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


def get(url, tries=2, timeout=30, raw=False):
    for i in range(tries):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "*/*",
                "Accept-Language": "ja,en;q=0.8"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                note("  ok %d B %.1fs %s" % (len(b), time.time() - t0, url[:80]))
                return r.status, (b if raw else b.decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            note("  HTTP %d %.1fs %s" % (e.code, time.time() - t0, url[:80]))
            if e.code == 404:
                return 404, (b"" if raw else "")
            time.sleep(3)
        except Exception as e:
            note("  ERR %s %.1fs %s" % (str(e)[:50], time.time() - t0, url[:80]))
            time.sleep(3)
    return None, (b"" if raw else "")


SC = {}
st, home = get("https://soundcloud.com/withr", timeout=40)
open(OUT + "/sc_home.html", "w", encoding="utf-8").write(home or "")
cid = None
try:
    m = re.search(r'window\.__sc_hydration\s*=\s*(\[.*?\]);', home or "", re.S)
    for x in json.loads(m.group(1)):
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
    for k, path in [
        ("user", "/users/%d" % uid),
        ("followings", "/users/%d/followings?limit=100" % uid),
        ("likes", "/users/%d/likes?limit=200" % uid),
        ("reposts", "/stream/users/%d/reposts?limit=200" % uid),
        ("mycomments", "/users/%d/comments?limit=200" % uid),
        ("tracks", "/users/%d/tracks?limit=200" % uid),
    ]:
        note("[sc] %s" % k)
        st, b = get("%s%s%sclient_id=%s" % (API, path, "&" if "?" in path else "?", cid))
        try:
            SC[k] = json.loads(b)
        except Exception:
            SC[k] = {"_raw": (b or "")[:2000], "_status": st}
        json.dump(SC, open(OUT + "/soundcloud.json", "w"), ensure_ascii=False, indent=1)
        time.sleep(1)

    tr = SC.get("tracks") or {}
    lst = tr.get("collection") if isinstance(tr, dict) else []
    SC["track_comments"] = {}
    for t in (lst or []):
        tid = t.get("id")
        note("[sc] comments %s" % t.get("title"))
        st, b = get("%s/tracks/%d/comments?limit=200&client_id=%s" % (API, tid, cid))
        try:
            SC["track_comments"][str(tid)] = json.loads(b)
        except Exception:
            SC["track_comments"][str(tid)] = {"_status": st}
        json.dump(SC, open(OUT + "/soundcloud.json", "w"), ensure_ascii=False, indent=1)
        time.sleep(0.8)

note("sc done")

TB = {}
for name, u in [
    ("api_read_json", "https://ucaliy.tumblr.com/api/read/json?num=50&start=0"),
    ("rss", "https://ucaliy.tumblr.com/rss"),
]:
    note("[tb] %s" % name)
    st, b = get(u, timeout=30)
    TB[name] = {"status": st, "body": (b or "")[:400000]}
json.dump(TB, open(OUT + "/tumblr.json", "w"), ensure_ascii=False, indent=1)

# 唯一一个 CDX：soundcloud 账号页
note("[cdx] soundcloud")
q = ("http://web.archive.org/cdx/search/cdx?url="
     + urllib.parse.quote("soundcloud.com/withr", safe="")
     + "&matchType=prefix&output=json&fl=timestamp,original,statuscode&filter=statuscode:200&limit=500")
st, body = get(q, tries=1, timeout=45)
rows = []
if body and body.strip().startswith("["):
    try:
        data = json.loads(body)
        if data and isinstance(data[0], list):
            rows = [dict(zip(data[0], r)) for r in data[1:]]
    except Exception as e:
        note("cdx parse fail %s" % e)
json.dump({"count": len(rows), "rows": rows},
          open(OUT + "/cdx_soundcloud.json", "w"), ensure_ascii=False)
note("cdx rows %d" % len(rows))
note("DONE")
