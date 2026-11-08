#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十四轮：下载 SoundCloud tristeza0810 全部 54 首音频

流程：用户页 -> apiClient(client_id) -> /users/id/tracks -> 逐首
      /media/soundcloud:tracks:<id>/stream/progressive -> CDN url -> 存 mp3
输出：out_jp14/mp3/*.mp3、manifest.json、曲目清单.md
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_jp14"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
MP3 = os.path.join(OUT, "mp3")
os.makedirs(RAW, exist_ok=True)
os.makedirs(MP3, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp14.txt"), "w", encoding="utf-8")


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
BUDGET = 2100


def dec(b):
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("utf-8", "replace")


def fetch(url, timeout=60, save=None):
    """返回 (status, bytes)"""
    if time.time() - T0 > BUDGET:
        return "SKIP", b""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "ja,en;q=0.8", "Referer": "https://soundcloud.com/"})
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
        return None, ("%s: %s" % (type(e).__name__, e)).encode()
    if save:
        open(save, "wb").write(b)
    return st, b


# ---- client_id ----
st, hb = fetch("https://soundcloud.com/tristeza0810", save=os.path.join(RAW, "user_page.html"))
html = dec(hb)
m = re.search(r"window\.__sc_hydration\s*=\s*(\[.*?\]);?\s*</script>", html, re.S)
hyd = json.loads(m.group(1)) if m else []
cid = None
uid = None
for b in hyd:
    if b.get("hydratable") == "apiClient":
        cid = (b.get("data") or {}).get("id")
    if b.get("hydratable") == "user":
        uid = (b["data"] or {}).get("id")
log("user", uid, "client_id", cid)

# ---- tracks ----
tracks = []
off = 0
while True:
    u = ("https://api-v2.soundcloud.com/users/%s/tracks?client_id=%s&limit=100&offset=%d"
         "&linked_partitioning=1&app_version=1740000000" % (uid, cid, off))
    st, b = fetch(u, save=os.path.join(RAW, "tracks_%d.json" % off))
    if st != 200:
        log("tracks fail", st)
        break
    d = json.loads(dec(b))
    tracks.extend(d.get("collection", []))
    if len(tracks) >= (54) or not d.get("next_href"):
        break
    off += 100
log("tracks", len(tracks))
json.dump(tracks, open(os.path.join(OUT, "tracks_all.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---- 逐首下载 ----
def safe(s):
    s = re.sub(r'[\\/:*?"<>|\n\r\t]', "_", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:80]

manifest = []
tracks.sort(key=lambda t: t.get("created_at") or "")
for i, t in enumerate(tracks, 1):
    tid = t["id"]
    title = t.get("title") or "untitled"
    fname = "%02d_%s_%s.mp3" % (i, tid, safe(title))
    path = os.path.join(MP3, fname)
    auth = t.get("track_authorization") or ""
    urls = [
        "https://api-v2.soundcloud.com/media/soundcloud:tracks:%s/stream/progressive?client_id=%s&track_authorization=%s"
        % (tid, cid, urllib.parse.quote(auth)),
        "https://api-v2.soundcloud.com/tracks/%s/stream/progressive?client_id=%s&track_authorization=%s"
        % (tid, cid, urllib.parse.quote(auth)),
        "https://api-v2.soundcloud.com/tracks/%s/stream?client_id=%s" % (tid, cid),
    ]
    ok = False
    note = ""
    for k, u in enumerate(urls):
        st, b = fetch(u)
        if st in (200, 302) and b:
            real = None
            if b[:1] == b"{":
                try:
                    j = json.loads(dec(b))
                    real = j.get("url")
                except Exception:
                    real = None
            if real:
                st2, ab = fetch(real, timeout=120)
                if st2 == 200 and len(ab) > 20000:
                    open(path, "wb").write(ab)
                    ok = True
                    note = "media-api#%d" % k
                    break
            elif len(b) > 20000 and b[:2] in (b"\xff\xfb", b"ID3"[:3], b"\xff\xf3", b"\xff\xf2"):
                open(path, "wb").write(b)
                ok = True
                note = "direct#%d" % k
                break
            elif len(b) > 20000 and b[:1] not in (b"{", b"<"):
                open(path, "wb").write(b)
                ok = True
                note = "raw#%d" % k
                break
        log("  try%d %s -> %s" % (k, tid, st))
        time.sleep(0.3)
    size = os.path.getsize(path) if ok and os.path.exists(path) else 0
    manifest.append({
        "n": i, "id": tid, "title": title, "file": fname if ok else None,
        "bytes": size, "ok": ok, "via": note,
        "created_at": t.get("created_at"), "duration_ms": t.get("full_duration") or t.get("duration"),
        "playback_count": t.get("playback_count"), "likes_count": t.get("likes_count"),
        "permalink_url": t.get("permalink_url"), "description": t.get("description"),
        "genre": t.get("genre"), "tag_list": t.get("tag_list"),
    })
    log("%02d/%d %s %s %s %d bytes %s" % (i, len(tracks), "OK " if ok else "FAIL", tid, title, size, note))
    time.sleep(0.4)

json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---- 清单 md ----
lines = ["# TRISTEZA / tristeza0810 — SoundCloud 全曲", "",
         "账号：https://soundcloud.com/tristeza0810", "",
         "| # | 日期 | 曲名 | 时长 | 播放 | 文件 |", "|---|---|---|---|---|---|"]
tot = 0
for m2 in manifest:
    dur = (m2["duration_ms"] or 0) // 1000
    tot += dur
    lines.append("| %02d | %s | %s | %d:%02d | %s | %s |" % (
        m2["n"], (m2["created_at"] or "")[:10], m2["title"].replace("|", "｜"),
        dur // 60, dur % 60, m2["playback_count"],
        m2["file"] or "未取到"))
lines += ["", "合计 %d 首，%d 小时 %d 分。" % (len(manifest), tot // 3600, (tot % 3600) // 60)]
open(os.path.join(OUT, "曲目清单.md"), "w", encoding="utf-8").write("\n".join(lines))
log("done ok=%d fail=%d" % (sum(1 for m2 in manifest if m2["ok"]),
                            sum(1 for m2 in manifest if not m2["ok"])))
