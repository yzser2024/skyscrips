#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十九轮：note 全 137 篇正文 + 第二 SoundCloud 账号 soukamakoto417

A. note.com/api/v2/creators/tristeza417/contents 翻完 14 页，取全部 key
B. 逐篇 /api/v3/notes/<key> 取正文，统计全部内嵌媒体
C. 用 resolve + 已存 client_id 拉 soukamakoto417 全量曲目与 playlist
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_jp19"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
NOTES = os.path.join(OUT, "notes")
os.makedirs(RAW, exist_ok=True)
os.makedirs(NOTES, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp19.txt"), "w", encoding="utf-8")


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
BUDGET = 1400


def get(url, save=None, timeout=45):
    if time.time() - T0 > BUDGET:
        return "SKIP", ""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})
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
    for enc in ("utf-8", "cp932"):
        try:
            return st, b.decode(enc)
        except UnicodeDecodeError:
            pass
    return st, b.decode("utf-8", "replace")


log("=" * 72)
log("A. note 文章清单翻页")
log("=" * 72)
keys = []
meta = {}
for p in range(1, 16):
    u = ("https://note.com/api/v2/creators/tristeza417/contents?kind=note&page=%d&per=10" % p)
    st, txt = get(u, save="contents_p%02d.json" % p)
    n = 0
    if st == 200:
        try:
            d = json.loads(txt)["data"]
            for c in d.get("contents", []):
                keys.append(c["key"])
                meta[c["key"]] = {"name": c.get("name"), "publishAt": c.get("publishAt"),
                                  "type": c.get("type"), "price": c.get("price"),
                                  "canRead": c.get("canRead")}
            n = len(d.get("contents", []))
            last = d.get("isLastPage")
            log("page %2d  %s  items=%d  last=%s  total=%s" % (p, st, n, last, d.get("totalCount")))
            if last:
                break
        except Exception as e:
            log("page %d json fail %s" % (p, e))
    else:
        log("page %2d  %s" % (p, st))
    if not n:
        break
    time.sleep(0.5)
keys = list(dict.fromkeys(keys))
log("TOTAL KEYS", len(keys))
json.dump(meta, open(os.path.join(OUT, "note_meta.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

log("")
log("=" * 72)
log("B. 逐篇正文")
log("=" * 72)
SVC = {}
SOUNDS = []
ATTS = []
YT = []
SC = []
AM = []
body_count = 0
for i, k in enumerate(keys, 1):
    u = "https://note.com/api/v3/notes/%s" % k
    st, txt = get(u, save=os.path.join("..", "notes", k + ".json"))
    b = ""
    if st == 200:
        try:
            b = json.loads(txt)["data"].get("body", "") or ""
            body_count += 1
        except Exception:
            pass
    for m in re.finditer(r'embedded-service="([^"]+)"', b):
        SVC[m.group(1)] = SVC.get(m.group(1), 0) + 1
    for m in re.finditer(r'data-identifier="([0-9a-f]{32})"', b):
        SOUNDS.append((k, meta.get(k, {}).get("name"), m.group(1)))
    for m in re.finditer(r'attachments/download/([0-9a-f]+)', b):
        ATTS.append((k, meta.get(k, {}).get("name"), m.group(1)))
    for m in re.finditer(r'youtube\.com/watch\?v=([0-9A-Za-z_-]+)', b):
        YT.append((k, meta.get(k, {}).get("name"), m.group(1)))
    for m in re.finditer(r'(soundcloud\.com/|on\.soundcloud\.com/)([^\s"&?]+)', b):
        SC.append((k, meta.get(k, {}).get("name"), m.group(0)))
    for m in re.finditer(r'(music\.apple\.com/[^\s"&?]+)', b):
        AM.append((k, meta.get(k, {}).get("name"), m.group(1)))
    if i % 20 == 0:
        log("  %3d/%d  bodies=%d  sounds=%d atts=%d yt=%d sc=%d" % (
            i, len(keys), body_count, len(SOUNDS), len(ATTS), len(YT), len(SC)))
    time.sleep(0.3)

log("")
log("SERVICES", json.dumps(SVC, ensure_ascii=False))
log("note-sound %d / attachment %d / youtube %d / soundcloud %d / applemusic %d" % (
    len(SOUNDS), len(ATTS), len(YT), len(SC), len(AM)))
json.dump({"sounds": SOUNDS, "attachments": ATTS, "youtube": YT,
           "soundcloud": SC, "applemusic": AM, "services": SVC},
          open(os.path.join(OUT, "media.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
for x in SOUNDS:
    log("  SOUND", x)
for x in ATTS:
    log("  ATT", x)

log("")
log("=" * 72)
log("C. 第二 SoundCloud 账号 soukamakoto417")
log("=" * 72)
CID = "QhVEWrrJKvW4uSU5u5EoI0FTXYUGzy5k"
res = "https://api-v2.soundcloud.com/resolve?url=https%3A%2F%2Fsoundcloud.com%2Fsoukamakoto417&client_id=" + CID
st, txt = get(res, save="sc_resolve.json")
uid = None
if st == 200:
    try:
        d = json.loads(txt)
        uid = d.get("id")
        log("resolve", st, "id", uid, "username", d.get("username"),
            "track_count", d.get("track_count"), "permalink", d.get("permalink"))
    except Exception as e:
        log("resolve json fail", e, txt[:200])
else:
    log("resolve", st, txt[:200])

if uid:
    tracks = []
    offset = 0
    for page in range(1, 12):
        u = ("https://api-v2.soundcloud.com/users/%s/tracks?client_id=%s"
             "&limit=100&offset=%d&linked_partitioning=1&app_version=1740000000"
             % (uid, CID, offset))
        st, txt = get(u, save="sc_tracks_p%02d.json" % page)
        if st != 200:
            log("tracks page", page, st)
            break
        try:
            d = json.loads(txt)
        except Exception:
            break
        coll = d.get("collection", [])
        tracks.extend(coll)
        log("tracks page", page, "got", len(coll), "total", len(tracks))
        nxt = d.get("next_href")
        if not nxt or not coll:
            break
        q = urllib.parse.parse_qs(urllib.parse.urlparse(nxt).query)
        try:
            offset = int(q.get("offset", ["0"])[0])
        except ValueError:
            break
        time.sleep(0.5)
    json.dump(tracks, open(os.path.join(OUT, "sc2_tracks.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    log("SC2 TOTAL", len(tracks))
    for t in tracks:
        log("  ", t.get("created_at", "")[:10], t.get("id"), t.get("title"),
            "|", (t.get("permalink_url") or "")[:70])
    st, txt = get("https://api-v2.soundcloud.com/users/%s/playlists?client_id=%s&limit=50&offset=0&linked_partitioning=1" % (uid, CID),
                  save="sc2_playlists.json")
    if st == 200:
        try:
            pls = json.loads(txt).get("collection", [])
            log("SC2 playlists", len(pls))
            for p in pls:
                log("   ", p.get("title"), p.get("track_count"))
        except Exception:
            pass

log("done in %ds" % int(time.time() - T0))
