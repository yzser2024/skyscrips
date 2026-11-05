# -*- coding: utf-8 -*-
"""probe7: 用 Twitter 官方 follow-button 数据接口核实 @ucaliy / @ucaliy17 是否存在；
   再兜底试 fxtwitter。全部只读公开接口。
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_ua7"
os.makedirs(OUT, exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
R = []


def note(s):
    line = "%s %s" % (time.strftime("%H:%M:%S"), s)
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()


def get(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(200000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read(50000).decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return None, str(e)[:80]


def add(tag, url, st, b):
    R.append({"tag": tag, "url": url, "status": st, "body": (b or "")[:1200]})
    note("%-26s %-5s %s" % (tag, st, (b or "")[:180].replace("\n", " ")))
    json.dump(R, open(OUT + "/probe7.json", "w"), ensure_ascii=False, indent=1)


# 1. Twitter 官方 follow-button 接口（不用登录）
for names in ["ucaliy", "ucaliy17", "withr17", "yunn"]:
    u = ("https://cdn.syndication.twimg.com/widgets/followbutton/info.json?screen_names="
         + urllib.parse.quote(names))
    st, b = get(u)
    add("syndication:" + names, u, st, b)
    time.sleep(2)

# 2. 第三方镜像 api.fxtwitter.com
for names in ["ucaliy", "ucaliy17"]:
    u = "https://api.fxtwitter.com/" + names
    st, b = get(u)
    add("fxtwitter:" + names, u, st, b)
    time.sleep(2)

# 3. Instagram 的公开 embed 接口（不登录也可能返回）
for names in ["ucaliy17", "ucaliy"]:
    u = "https://www.instagram.com/%s/embed/" % names
    st, b = get(u, timeout=30)
    add("ig-embed:" + names, u, st, b)
    time.sleep(3)

# 4. 她的站 2014 年之后是否还有 Twitter 链接（直接看存档页）
for ts, path in [("20141228174819", "index.html"), ("20190330163122", "about.html")]:
    u = ("http://web.archive.org/web/%sid_/http://music.geocities.jp/withr17/%s" % (ts, path))
    st, b = get(u, timeout=40)
    low = (b or "").lower()
    add("site:%s@%s" % (path, ts), u, st,
        "twitter=%s tumblr=%s ucaliy=%s len=%d" % (
            "twitter" in low, "tumblr" in low, "ucaliy" in low, len(b or "")))
    time.sleep(6)

note("DONE")
