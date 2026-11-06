# -*- coding: utf-8 -*-
"""probe_allnames3: 补第一二轮的三个空白——Instagram（429）、YouTube（JS 壳）、GitHub repo。
   只取事实字段，不做结论。
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

OUT = "out_a3"
os.makedirs(OUT, exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")


def note(s):
    line = "%s %s" % (time.strftime("%H:%M:%S"), s)
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()


def get(url, headers=None, timeout=25):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "ja,en;q=0.8"}
    h.update(headers or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
            return r.status, r.read(1200000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read(60000).decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return None, "ERR:" + str(e)[:80]


res = {}

# ---- 1) Instagram web_profile_info
IGH = {"x-ig-app-id": "936619743392459",
       "Referer": "https://www.instagram.com/",
       "Accept": "*/*"}
for n in ["withr", "withr17", "ucaliy", "ucaliy17", "yunn", "rico", "yukari"]:
    u = "https://i.instagram.com/api/v1/users/web_profile_info/?username=" + n
    st, b = get(u, IGH)
    rec = {"status": st}
    try:
        j = json.loads(b)
        us = (j.get("data") or {}).get("user")
        if us:
            rec.update({k: us.get(k) for k in
                        ("id", "username", "full_name", "biography", "external_url",
                         "edge_followed_by", "edge_follow", "is_private", "is_verified")})
            rec["posts"] = ((us.get("edge_owner_to_timeline_media") or {}).get("count"))
            rec["pic"] = (us.get("profile_pic_url_hd") or "")[:120]
        else:
            rec["msg"] = (j.get("message") or "")[:120]
    except Exception:
        rec["raw"] = (b or "")[:250]
    res["ig_" + n] = rec
    note("ig %-9s %-4s %s" % (n, st, json.dumps(rec, ensure_ascii=False)[:190]))
    time.sleep(4)

# ---- 2) YouTube：取 about 页里的 ytInitialData
for n in ["@withr", "@yunn", "@hayato-xh5xc"]:
    u = "https://www.youtube.com/%s/about" % n
    st, b = get(u, {"Accept-Language": "ja,en;q=0.8"})
    rec = {"status": st, "len": len(b or "")}
    m = re.search(r'"channelMetadataRenderer":\{"title":"(.*?)","description":"(.*?)"', b or "")
    if m:
        rec["title"] = m.group(1)[:80]
        rec["desc"] = m.group(2)[:400]
    m = re.search(r'"canonicalBaseUrl":"(.*?)"', b or "")
    if m:
        rec["canonical"] = m.group(1)
    m = re.search(r'"subscriberCountText":\{"accessibility":\{"accessibilityData":\{"label":"(.*?)"', b or "")
    if m:
        rec["subs"] = m.group(1)
    for kw in ["withr", "With R", "ゆん", "yunn", "rico", "案山子"]:
        if kw.lower() in (b or "").lower():
            rec.setdefault("hits", []).append(kw)
    res["yt_" + n] = rec
    note("yt %-15s %-4s %s" % (n, st, json.dumps(rec, ensure_ascii=False)[:200]))
    time.sleep(3)

# ---- 3) GitHub：yunn / oneyunn 的 repo 名
for n in ["yunn", "oneyunn"]:
    st, b = get("https://api.github.com/users/%s/repos?per_page=20&sort=updated" % n)
    items = []
    try:
        for r in json.loads(b):
            items.append((r.get("name"), r.get("description"), r.get("language"),
                          r.get("created_at"), r.get("updated_at")))
    except Exception:
        pass
    res["ghrepos_" + n] = {"status": st, "items": items}
    note("ghrepos %-9s %s %s" % (n, st, json.dumps(items, ensure_ascii=False)[:200]))
    time.sleep(2)

json.dump(res, open(OUT + "/detail3.json", "w"), ensure_ascii=False, indent=1)
note("DONE")
