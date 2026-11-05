# -*- coding: utf-8 -*-
"""probe8: 取 fxtwitter 的完整 user 对象（name/description/created_at/头像），
并解析 instagram embed 判断账号是否有效。"""
import json
import os
import re
import time
import urllib.error
import urllib.request

OUT = "out_ua8"
os.makedirs(OUT, exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    line = "%s %s" % (time.strftime("%H:%M:%S"), s)
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()


def get(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(400000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read(50000).decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return None, str(e)[:80]


res = {}
for n in ["ucaliy", "ucaliy17", "withr17", "yunn", "oneyunn"]:
    st, b = get("https://api.fxtwitter.com/" + n)
    note("== %s status=%s" % (n, st))
    try:
        d = json.loads(b)
        u = d.get("user") or {}
        keep = {k: u.get(k) for k in
                ["id", "screen_name", "name", "description", "location",
                 "url", "followers", "following", "likes", "tweets",
                 "media_count", "joined", "avatar_url", "banner_url",
                 "verification", "protected"]}
        res[n] = {"status": st, "user": keep, "raw_msg": d.get("message")}
        for k, v in keep.items():
            note("   %-14s %s" % (k, str(v)[:150]))
    except Exception as e:
        res[n] = {"status": st, "raw": (b or "")[:400], "err": str(e)}
        note("   raw %s" % (b or "")[:200])
    time.sleep(3)

json.dump(res, open(OUT + "/twitter.json", "w"), ensure_ascii=False, indent=1)

# Instagram embed 判活
for n in ["ucaliy17", "ucaliy"]:
    st, b = get("https://www.instagram.com/%s/embed/" % n, timeout=30)
    low = (b or "").lower()
    hit = [k for k in ["sorry, this page", "isn't available", "page not found"] if k in low]
    m = re.search(r'class="UsernameText"[^>]*>(.*?)<', b or "")
    title = re.search(r"<title>(.*?)</title>", b or "", re.S)
    note("ig-embed %s status=%s hits=%s username=%s title=%s" % (
        n, st, hit, m.group(1) if m else "", (title.group(1) if title else "")[:60]))
    res["ig_" + n] = {"status": st, "hits": hit,
                      "username": m.group(1) if m else "",
                      "title": (title.group(1) if title else "")[:100]}
    time.sleep(4)

json.dump(res, open(OUT + "/twitter.json", "w"), ensure_ascii=False, indent=1)
note("DONE")
