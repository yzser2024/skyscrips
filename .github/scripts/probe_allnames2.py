# -*- coding: utf-8 -*-
"""probe_allnames2: 第二轮——把第一轮里「200 但不知道是谁」的候选逐个打开看正文。
不给结论，只存原文与判定所需的字段（title / bio / 首屏文字 / 时间）。
"""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request

OUT = "out_a2"
os.makedirs(OUT, exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    line = "%s %s" % (time.strftime("%H:%M:%S"), s)
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()


def get(url, timeout=25, referer=None, raw=False):
    h = {"User-Agent": UA, "Accept": "*/*",
         "Accept-Language": "ja,en-US;q=0.8,en;q=0.6"}
    if referer:
        h["Referer"] = referer
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read(900000)
            return r.status, (b if raw else b.decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            b = e.read(80000)
            return e.code, (b if raw else b.decode("utf-8", "replace"))
        except Exception:
            return e.code, (b"" if raw else "")
    except Exception as e:
        return None, (b"" if raw else "ERR:" + str(e)[:80])


def text(html):
    t = re.sub(r"<script.*?</script>", " ", html or "", flags=re.S)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[ \t\u3000]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


res = {}

# 1) 逐页全文
PAGES = [
    ("ameblo_withr", "https://ameblo.jp/withr/"),
    ("sc_yunn", "https://soundcloud.com/yunn"),
    ("gh_yunn", "https://github.com/yunn"),
    ("gh_oneyunn", "https://github.com/oneyunn"),
    ("gh_withr", "https://github.com/withr"),
    ("tumblr_withr17", "https://www.tumblr.com/withr17"),
    ("ig_withr", "https://www.instagram.com/withr/"),
    ("ig_withr17", "https://www.instagram.com/withr17/"),
    ("yt_withr", "https://www.youtube.com/@withr"),
    ("yt_yunn", "https://www.youtube.com/@yunn"),
    ("yt_hayato", "https://www.youtube.com/@hayato-xh5xc/videos"),
]
for tag, u in PAGES:
    st, h = get(u, referer="https://www.google.com/")
    t = text(h)
    res[tag] = {"url": u, "status": st, "len": len(h or ""), "text": t[:6000]}
    note("%-14s %-4s len=%-7d %s" % (tag, st, len(h or ""), t[:120].replace("\n", " ")))
    time.sleep(3)

# 2) GitHub API（结构化，最可靠）
for n in ["yunn", "oneyunn", "withr", "withr17"]:
    st, b = get("https://api.github.com/users/" + n)
    rec = {"status": st}
    try:
        j = json.loads(b)
        for k in ("login", "name", "bio", "blog", "location", "created_at",
                  "public_repos", "followers", "email", "company", "twitter_username"):
            rec[k] = j.get(k)
    except Exception:
        rec["raw"] = (b or "")[:200]
    res["ghapi_" + n] = rec
    note("ghapi %-9s %s %s" % (n, st, json.dumps(rec, ensure_ascii=False)[:170]))
    time.sleep(2)

# 3) 推特 syndication（拿最近一条推文正文）
for n in ["yunn", "withR", "ucaliy", "withr17"]:
    st, h = get("https://syndication.twitter.com/srv/timeline-profile/screen-name/" + n, timeout=30)
    t = text(h)
    res["synd_" + n] = {"status": st, "len": len(h or ""), "text": t[:2500]}
    note("synd %-9s %-4s %s" % (n, st, t[:150].replace("\n", " ")))
    time.sleep(4)

# 4) Gravatar：两个邮箱是否注册过头像
for mail in ["withr17@gmail.com", "yunnyunn177@yahoo.co.jp"]:
    md5 = hashlib.md5(mail.strip().lower().encode()).hexdigest()
    st, _ = get("https://www.gravatar.com/avatar/%s?d=404" % md5, timeout=20, raw=True)
    st2, b2 = get("https://www.gravatar.com/%s.json" % md5, timeout=20)
    res["grav_" + mail] = {"md5": md5, "avatar_status": st,
                           "profile_status": st2, "profile": (b2 or "")[:600]}
    note("grav %-28s avatar=%-4s profile=%-4s" % (mail, st, st2))
    time.sleep(2)

# 5) 域名：withr17.net 是否还存在
for dom in ["withr17.net"]:
    for rp in ["https://rdap.org/domain/" + dom,
               "https://rdap.verisign.com/net/v1/domain/" + dom]:
        st, b = get(rp, timeout=25)
        res["rdap_" + rp.split("//")[1][:12] + "_" + dom] = {"status": st, "body": (b or "")[:1500]}
        note("rdap %-46s %s" % (rp, st))
        time.sleep(2)

# 6) GitHub 用户搜索
for q in ["withr17", "oneyunn", "yunn"]:
    st, b = get("https://api.github.com/search/users?q=" + q)
    try:
        j = json.loads(b)
        items = [(x["login"], x["html_url"]) for x in j.get("items", [])[:8]]
    except Exception:
        items = []
    res["ghsearch_" + q] = {"status": st, "total": (j.get("total_count") if items or True else None),
                            "items": items, "raw": (b or "")[:300]}
    note("ghsearch %-9s %s total=%s" % (q, st, res["ghsearch_" + q].get("total")))
    time.sleep(3)

json.dump(res, open(OUT + "/detail.json", "w"), ensure_ascii=False, indent=1)
note("DONE")
