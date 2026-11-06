# -*- coding: utf-8 -*-
"""probe_allnames: 对 yukari / yunn / ゆん / rico / withr17 等 8 个名字，
   在 30 个平台 + Wayback CDX + 推特镜像 + 搜索引擎 + RDAP 上做一次全量核查。
   判定只写事实：返回码、页面标题、是否命中关联词，不做结论。
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_an"
os.makedirs(OUT, exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    line = "%s %s" % (time.strftime("%H:%M:%S"), s)
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()


def get(url, timeout=20, referer=None):
    h = {"User-Agent": UA, "Accept": "*/*",
         "Accept-Language": "ja,en-US;q=0.8,en;q=0.6"}
    if referer:
        h["Referer"] = referer
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(600000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read(60000).decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return None, "ERR:" + str(e)[:70]


RELATED = ["withr", "with r", "ゆん", "yunn", "oneyunn", "oneyunn79",
           "ucaliy", "geocities.jp/withr", "作編曲", "作曲", "midi", "ｒｉｃｏ"]


def meta(html):
    """抓标题、og:description、是否命中关联词"""
    t = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.S | re.I)
    if m:
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()[:160]
    d = ""
    m = re.search(r'<meta[^>]+(?:name|property)=["\'](?:og:)?description["\'][^>]+content=["\'](.*?)["\']',
                  html or "", re.S | re.I)
    if m:
        d = re.sub(r"\s+", " ", m.group(1))[:200]
    low = (html or "").lower()
    hits = [k for k in RELATED if k in low]
    return t, d, hits


# ---------------------------------------------------------------- 1. 平台
NAMES = ["yukari", "yunn", "yun", "rico", "withr17", "withr", "oneyunn",
         "%E3%82%86%E3%82%93"]  # 最后一个 = 「ゆん」percent-encoded

PLAT = [
    ("instagram", "https://www.instagram.com/{n}/"),
    ("soundcloud", "https://soundcloud.com/{n}"),
    ("youtube", "https://www.youtube.com/@{n}"),
    ("note", "https://note.com/{n}"),
    ("github", "https://github.com/{n}"),
    ("tumblr_sub", "https://{n}.tumblr.com/"),
    ("threads", "https://www.threads.net/@{n}"),
    ("tiktok", "https://www.tiktok.com/@{n}"),
    ("pinterest", "https://www.pinterest.com/{n}/"),
    ("twitch", "https://www.twitch.tv/{n}"),
    ("deviantart", "https://www.deviantart.com/{n}"),
    ("vimeo", "https://vimeo.com/{n}"),
    ("flickr", "https://www.flickr.com/people/{n}"),
    ("ameblo", "https://ameblo.jp/{n}/"),
    ("fc2blog", "https://{n}.blog.fc2.com/"),
    ("livedoor", "https://{n}.blog.jp/"),
    ("seesaa", "https://{n}.seesaa.net/"),
    ("pixiv", "https://www.pixiv.net/users/{n}"),
    ("spotify", "https://open.spotify.com/user/{n}"),
    ("aboutme", "https://about.me/{n}"),
    ("medium", "https://medium.com/@{n}"),
    ("substack", "https://{n}.substack.com"),
    ("litlink", "https://lit.link/{n}"),
    ("mstdn", "https://mstdn.jp/api/v1/accounts/lookup?acct={n}"),
    ("misskey", "https://misskey.io/@{n}"),
    ("bluesky", "https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle={n}.bsky.social"),
    ("reddit", "https://www.reddit.com/user/{n}/about.json"),
    ("bandcamp", "https://bandcamp.com/{n}"),
    ("mixcloud", "https://www.mixcloud.com/{n}/"),
    ("carrd", "https://{n}.carrd.co/"),
]

rows = []
for n in NAMES:
    for plat, tpl in PLAT:
        u = tpl.format(n=n)
        st, b = get(u)
        t, d, hits = meta(b)
        rows.append({"name": n, "platform": plat, "url": u, "status": st,
                     "title": t, "desc": d, "hits": hits,
                     "len": len(b or "")})
        flag = "HIT:" + ",".join(hits) if hits else ""
        note("%-9s %-11s %-4s %-6s %s %s" % (n, plat, st, len(b or ""), t[:70], flag))
        time.sleep(1.2)

json.dump(rows, open(OUT + "/platforms.json", "w"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- 2. 推特镜像
mir = []
for n in NAMES[:7]:
    u = "https://api.fxtwitter.com/" + n
    st, b = get(u)
    rec = {"name": n, "status": st, "raw": (b or "")[:1500]}
    try:
        j = json.loads(b)
        rec["code"] = j.get("code")
        rec["msg"] = j.get("message")
        us = j.get("user") or {}
        rec["user"] = {k: us.get(k) for k in
                       ("id", "screen_name", "name", "description", "location",
                        "url", "joined", "followers", "following", "tweets",
                        "protected", "avatar_url")}
    except Exception as e:
        rec["parse"] = str(e)[:60]
    mir.append(rec)
    note("tw %-9s %s %s" % (n, st, json.dumps(rec.get("user", rec.get("msg")), ensure_ascii=False)[:180]))
    time.sleep(2)

json.dump(mir, open(OUT + "/twitter.json", "w"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- 3. Wayback CDX
CDX = "http://web.archive.org/cdx/search/cdx?url={u}&matchType=prefix&output=json&fl=original,timestamp,statuscode&filter=statuscode:200&limit=25&collapse=urlkey"
cdx = {}
TARGETS = [
    ("twitter", "twitter.com/{n}"),
    ("x", "x.com/{n}"),
    ("instagram", "instagram.com/{n}"),
    ("soundcloud", "soundcloud.com/{n}"),
    ("pixiv", "pixiv.net/member.php?nick={n}"),
    ("ameblo", "ameblo.jp/{n}"),
    ("tumblr", "{n}.tumblr.com"),
]
for n in NAMES[:7]:
    for tag, tpl in TARGETS:
        u = tpl.format(n=n)
        st, b = get(CDX.format(u=urllib.parse.quote(u, safe="")), timeout=45)
        cnt, sample = 0, []
        try:
            j = json.loads(b)
            cnt = max(0, len(j) - 1)
            sample = j[1:6]
        except Exception:
            pass
        cdx["%s|%s" % (n, tag)] = {"status": st, "count": cnt, "sample": sample,
                                   "len": len(b or "")}
        note("cdx %-9s %-11s %-4s n=%d" % (n, tag, st, cnt))
        time.sleep(2)

json.dump(cdx, open(OUT + "/cdx.json", "w"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- 4. 搜索引擎
Q = [
    '"withr17"',
    '"with r" ゆん rico 音楽',
    '"oneyunn"',
    '"yunn" "with r"',
    '"ucaliy" -ucaliy17',
    '"with R" "Final Tale"',
    '"案山子島" with R',
    '"rico" "with R" 作曲',
    '"withr17.net"',
    '"ゆん" "作編曲" geocities',
]
eng = {}
for q in Q:
    for tag, tpl in [("ddg", "https://html.duckduckgo.com/html/?q={q}"),
                     ("bing", "https://www.bing.com/search?q={q}&setlang=ja")]:
        u = tpl.format(q=urllib.parse.quote(q))
        st, b = get(u, timeout=25)
        txt = re.sub(r"<script.*?</script>", " ", b or "", flags=re.S)
        txt = re.sub(r"<style.*?</style>", " ", txt, flags=re.S)
        txt = re.sub(r"<[^>]+>", " ", txt)
        txt = re.sub(r"\s+", " ", txt)
        eng["%s|%s" % (tag, q)] = {"status": st, "len": len(b or ""), "text": txt[:1800]}
        note("se %-5s %-32s %-4s %s" % (tag, q[:32], st, txt[:110]))
        time.sleep(2)

json.dump(eng, open(OUT + "/search.json", "w"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- 5. RDAP / 站点
extra = {}
for u, tag in [("https://rdap.verisign.com/net/v1/domain/withr17.net", "rdap_withr17net"),
               ("https://rdap.verisign.com/net/v1/domain/with-r.net", "rdap_withr"),
               ("https://www.youtube.com/@hayato-xh5xc/about", "yt_hayato"),
               ("https://api.search.nicovideo.jp/api/v2/snapshot/video/contents/search?q=with%20R&targets=title,description,tags&fields=contentId,title,startTime,userId,viewCounter&_sort=-viewCounter&_limit=30&_context=probe",
                "nico_search_withr"),
               ("https://api.search.nicovideo.jp/api/v2/snapshot/video/contents/search?q=%E6%A1%88%E5%B1%B1%E5%AD%90%E5%B3%B6&targets=title,description,tags&fields=contentId,title,startTime,userId,viewCounter&_limit=30&_context=probe",
                "nico_search_kakashi"),
               ("https://api.search.nicovideo.jp/api/v2/snapshot/video/contents/search?q=%E3%82%86%E3%82%93%20with%20R&targets=title,description,tags&fields=contentId,title,startTime,userId,viewCounter&_limit=30&_context=probe",
                "nico_search_yun")]:
    st, b = get(u, timeout=35)
    extra[tag] = {"status": st, "body": (b or "")[:20000]}
    note("ex %-20s %-4s %s" % (tag, st, (b or "")[:140].replace("\n", " ")))
    time.sleep(3)

json.dump(extra, open(OUT + "/extra.json", "w"), ensure_ascii=False, indent=1)
note("DONE rows=%d" % len(rows))
