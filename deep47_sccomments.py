# -*- coding: utf-8 -*-
"""deep-47: SoundCloud 评论区挖掘（她本人回复的时间线，2014-2016）"""
import os, json, time, urllib.request, urllib.error

OUT = "out_deep47"
os.makedirs(OUT, exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"


def note(s):
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def get(url, tries=3, timeout=45):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            note("    HTTP %d" % e.code)
            time.sleep(2 + i * 4)
        except Exception as e:
            note("    ERR %s" % str(e)[:60])
            time.sleep(2 + i * 4)
    return None, ""


# client_id 从首页 hydration 重新取
st, h = get("https://soundcloud.com/withr")
import re
m = re.search(r'window\.__sc_hydration\s*=\s*(\[.*?\]);', h or "", re.S)
data = json.loads(m.group(1)) if m else []
client = uid = None
for x in data:
    if x.get("hydratable") == "apiClient":
        client = x["data"].get("id")
    if x.get("hydratable") == "user":
        uid = x["data"].get("id")
note("client=%s uid=%s" % (client, uid))
if not client:
    note("无 client_id")
    raise SystemExit

# 她的评论（作为评论者）
st, t = get("https://api-v2.soundcloud.com/users/%s/comments?client_id=%s&limit=200" % (uid, client))
open(OUT + "/my_comments.json", "w").write(t or "")
try:
    j = json.loads(t)
    coll = j.get("collection", [])
    note("= 她本人的评论 %d 条" % len(coll))
    for c in coll:
        note("  %s | track=%s | %s" % (c.get("created_at", "")[:10],
                                       str(c.get("track_id")), (c.get("body") or "").replace("\n", " ")[:150]))
except Exception as e:
    note("解析失败 %s" % e)

# 每首曲的评论
st, t = get("https://api-v2.soundcloud.com/users/%s/tracks?client_id=%s&limit=100" % (uid, client))
tr = json.loads(t)
tracks = tr.get("collection", [])
note("曲目 %d" % len(tracks))
allc = []
for tk in tracks:
    tid = tk.get("id")
    st, t = get("https://api-v2.soundcloud.com/tracks/%s/comments?client_id=%s&limit=100" % (tid, client))
    if not t:
        continue
    try:
        j = json.loads(t)
        coll = j.get("collection", [])
    except Exception:
        continue
    note("曲《%s》评论 %d 条" % (tk.get("title"), len(coll)))
    for c in coll:
        allc.append({"track": tk.get("title"), "ts": c.get("created_at"),
                     "user": (c.get("user") or {}).get("username"),
                     "uid": (c.get("user") or {}).get("id"),
                     "body": c.get("body")})
    time.sleep(1.5)

json.dump(allc, open(OUT + "/all_comments.json", "w"), ensure_ascii=False, indent=1)
note("总评论 %d" % len(allc))
# 她自己的回复
mine = [c for c in allc if str(c.get("uid")) == str(uid)]
note("其中她本人回复 %d 条" % len(mine))
for c in mine:
    note("  %s | %s | %s" % (c["ts"][:10] if c["ts"] else "?", c["track"], (c["body"] or "").replace("\n", " ")[:200]))
note("done")
