#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十三轮：抓 SoundCloud 用户 tristeza0810 的全部曲目元数据

1. 打开用户页，取 __sc_hydration（user id / track_count）
2. 从页面引用的 app js 里刮 client_id
3. 分页拉 /users/<id>/tracks，直到取完
4. 顺带拉 playlists（album）
5. 输出 tracks_all.json + tracks.csv + 统计
"""
import csv
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_jp13"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp13.txt"), "w", encoding="utf-8")


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


def dec(b):
    for enc in ("utf-8", "cp932"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", "replace")


def get(url, save=None, timeout=40, headers=None):
    if time.time() - T0 > BUDGET:
        return "SKIP", ""
    h = {"User-Agent": UA, "Accept-Language": "ja,en;q=0.8",
         "Accept": "text/html,application/json,*/*"}
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
    return st, dec(b)


# ---------- 1. 用户页 ----------
st, html = get("https://soundcloud.com/tristeza0810", save="user_page.html")
log("user page", st, len(html))
hyd = []
for m in re.finditer(r"window\.__sc_hydration\s*=\s*(\[.*?\]);?\s*</script>", html, re.S):
    try:
        hyd = json.loads(m.group(1))
        break
    except Exception:
        pass
log("hydration blocks", [b.get("hydratable") for b in hyd])
user = {}
for b in hyd:
    if b.get("hydratable") == "user":
        user = b["data"]
open(os.path.join(RAW, "hydration_user.json"), "w", encoding="utf-8").write(
    json.dumps(user, ensure_ascii=False, indent=1))
log("user:", user.get("id"), user.get("permalink"), user.get("username"),
    "tracks:", user.get("track_count"), "followers:", user.get("followers_count"))

# ---------- 2. client_id ----------
js_urls = re.findall(r'<script[^>]+src="(https://a-v2\.sndcdn\.com/assets/[^"]+\.js)"', html)
log("js assets", len(js_urls))
client_id = None
for u in js_urls[:8]:
    st2, js = get(u)
    if not js:
        continue
    for pat in (r'client_id\s*:\s*"([0-9a-zA-Z]{32})"',
                r'client_id=([0-9a-zA-Z]{32})',
                r'"client_id":"([0-9a-zA-Z]{32})"'):
        mm = re.search(pat, js)
        if mm:
            client_id = mm.group(1)
            log("client_id found in", u.split("/")[-1], "->", client_id)
            break
    if client_id:
        break
# 备用：页面内联
if not client_id:
    mm = re.search(r'client_id["\']?\s*[:=]\s*["\']([0-9a-zA-Z]{32})', html)
    if mm:
        client_id = mm.group(1)
        log("client_id from page inline")
log("client_id:", client_id)

json.dump({"client_id": client_id, "user": user},
          open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

if not client_id:
    log("ABORT: no client_id")
    raise SystemExit(0)

uid = user.get("id")

# ---------- 3. 分页拉曲目 ----------
tracks = []
offset = 0
page = 0
while True:
    page += 1
    url = ("https://api-v2.soundcloud.com/users/%s/tracks?client_id=%s"
           "&limit=100&offset=%d&linked_partitioning=1&app_version=1740000000"
           % (uid, client_id, offset))
    st3, body = get(url, save="tracks_p%02d.json" % page)
    log("tracks page", page, "status", st3, "offset", offset, "bytes", len(body) if body else 0)
    if st3 != 200 or not body:
        break
    try:
        d = json.loads(body)
    except Exception as e:
        log("  json fail", e)
        break
    coll = d.get("collection", [])
    tracks.extend(coll)
    log("  got", len(coll), "total", len(tracks))
    nxt = d.get("next_href")
    if not nxt or not coll:
        break
    # 解析 next_href 里的 offset
    q = urllib.parse.parse_qs(urllib.parse.urlparse(nxt).query)
    offset = int(q.get("offset", ["0"])[0])
    if page > 30:
        break
    time.sleep(0.6)

log("TOTAL TRACKS", len(tracks))
json.dump(tracks, open(os.path.join(OUT, "tracks_all.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---------- 4. playlists ----------
pls = []
pst, pbody = get("https://api-v2.soundcloud.com/users/%s/playlists?client_id=%s&limit=50&offset=0&linked_partitioning=1"
                 % (uid, client_id), save="playlists.json")
if pst == 200 and pbody:
    try:
        pls = json.loads(pbody).get("collection", [])
    except Exception:
        pls = []
log("playlists", len(pls))
json.dump(pls, open(os.path.join(OUT, "playlists_all.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---------- 5. 汇总表 ----------
rows = []
for t in tracks:
    rows.append({
        "id": t.get("id"),
        "title": t.get("title"),
        "created_at": t.get("created_at"),
        "display_date": t.get("display_date"),
        "last_modified": t.get("last_modified"),
        "duration_ms": t.get("full_duration") or t.get("duration"),
        "playback_count": t.get("playback_count"),
        "likes_count": t.get("likes_count"),
        "reposts_count": t.get("reposts_count"),
        "comment_count": t.get("comment_count"),
        "genre": t.get("genre"),
        "tag_list": t.get("tag_list"),
        "permalink": t.get("permalink"),
        "permalink_url": t.get("permalink_url"),
        "description": (t.get("description") or "").replace("\n", " "),
        "license": t.get("license"),
        "downloadable": t.get("downloadable"),
        "streamable": t.get("streamable"),
        "artwork_url": t.get("artwork_url"),
        "track_authorization": t.get("track_authorization"),
    })
rows.sort(key=lambda r: r["created_at"] or "")
with open(os.path.join(OUT, "tracks.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["id"])
    w.writeheader()
    w.writerows(rows)

total_ms = sum((r["duration_ms"] or 0) for r in rows)
log("total duration hours %.2f" % (total_ms / 3600000.0))
for r in rows:
    log("%s | %s | %s | %s | %s" % ((r["created_at"] or "")[:10], r["id"], r["title"],
                                    (r["duration_ms"] or 0) // 1000, r["playback_count"]))
log("done")
