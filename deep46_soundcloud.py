# -*- coding: utf-8 -*-
"""deep-46: SoundCloud「With R」(id 123211690) 深挖
- 取 client_id → 调 api-v2 拿 tracks / web-profiles / likes
- web-profiles 可能暴露她绑定的 twitter / instagram
"""
import os, re, json, time, urllib.request, urllib.error

OUT = "out_deep46"
os.makedirs(OUT, exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def get(url, tries=4, timeout=45, raw=False):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                return r.status, (b if raw else b.decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            note("    HTTP %d %s" % (e.code, url[:90]))
            time.sleep(3 + i * 5)
            continue
        except Exception as e:
            note("    ERR %s" % str(e)[:70])
            time.sleep(3 + i * 5)
    return None, "" if not raw else b""


# 1) 首页取 client_id
st, h = get("https://soundcloud.com/withr")
open(OUT + "/home.html", "w").write(h or "")
m = re.search(r'window\.__sc_hydration\s*=\s*(\[.*?\]);', h or "", re.S)
data = json.loads(m.group(1)) if m else []
client = None
uid = None
for x in data:
    if x.get("hydratable") == "apiClient":
        client = x["data"].get("id")
    if x.get("hydratable") == "user":
        uid = x["data"].get("id")
note("client_id=%s user_id=%s" % (client, uid))
if not client or not uid:
    note("缺 client_id / user_id，结束")
    raise SystemExit

# 2) web-profiles
st, t = get("https://api-v2.soundcloud.com/users/%s/web-profiles?client_id=%s" % (uid, client))
open(OUT + "/web_profiles.json", "w").write(t or "")
note("web-profiles -> %s len=%d" % (st, len(t or "")))
try:
    for wp in json.loads(t):
        note("  平台=%-12s 名=%-20s 链接=%s" % (wp.get("service"), wp.get("title"), wp.get("url")))
except Exception as e:
    note("  解析失败 %s" % e)

# 3) user 详情
st, t = get("https://api-v2.soundcloud.com/users/%s?client_id=%s" % (uid, client))
open(OUT + "/user.json", "w").write(t or "")
try:
    u = json.loads(t)
    note("user: %s | created=%s | tracks=%s | followers=%s | desc=%s"
         % (u.get("username"), u.get("created_at"), u.get("track_count"),
            u.get("followers_count"), (u.get("description") or "").replace("\n", " ")[:200]))
except Exception:
    pass

# 4) tracks
st, t = get("https://api-v2.soundcloud.com/users/%s/tracks?client_id=%s&limit=100&linked_partitioning=true" % (uid, client))
open(OUT + "/tracks.json", "w").write(t or "")
note("tracks -> %s len=%d" % (st, len(t or "")))
tracks = []
try:
    j = json.loads(t)
    tracks = j.get("collection", j if isinstance(j, list) else [])
except Exception as e:
    note("  tracks 解析失败 %s" % e)

note("曲目 %d 首：" % len(tracks))
for tr in tracks:
    note("  %s | %s | %s | plays=%s | desc=%s"
         % (tr.get("created_at", "")[:10], tr.get("title"),
            tr.get("permalink_url", "")[-40:], tr.get("playback_count"),
            (tr.get("description") or "").replace("\n", " ")[:80]))

# 5) likes / reposts
for kind in ["likes", "reposts", "followings"]:
    st, t = get("https://api-v2.soundcloud.com/users/%s/%s?client_id=%s&limit=50" % (uid, kind, client))
    open(OUT + "/%s.json" % kind, "w").write(t or "")
    try:
        j = json.loads(t)
        coll = j.get("collection", [])
        note("%s -> %s 条" % (kind, len(coll)))
        for it in coll[:25]:
            note("   %s %s" % (it.get("created_at", "")[:10], it.get("title") or it.get("username")))
    except Exception:
        note("%s -> %s" % (kind, st))

note("done")
