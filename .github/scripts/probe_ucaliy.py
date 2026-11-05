# -*- coding: utf-8 -*-
"""probe_ucaliy: 用同一个 handle「ucaliy」去各平台探一遍。
原则：只记录实际返回的状态码 / 标题 / 关键文本，不做推断。
输出 out_ua/probe.json + log.txt
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_ua"
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


def fetch(url, timeout=25, headers=None, tries=1):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "ja,en;q=0.8"}
    if headers:
        h.update(headers)
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(600000)
                return r.status, raw.decode("utf-8", "replace"), dict(r.headers)
        except urllib.error.HTTPError as e:
            try:
                body = e.read(200000).decode("utf-8", "replace")
            except Exception:
                body = ""
            return e.code, body, dict(e.headers or {})
        except Exception as e:
            last = str(e)[:60]
    return None, last or "", {}


def title_of(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.S | re.I)
    if not m:
        return ""
    t = re.sub(r"<[^>]+>", "", m.group(1))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:160]


def desc_of(html):
    m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
                  html or "", re.S | re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip()[:200] if m else ""


DEAD_WORDS = [
    "page not found", "ページが見つかりません", "お探しのページ",
    "isn't available", "is not available", "couldn't find", "could not find",
    "not found", "no longer available", "doesn't exist", "does not exist",
    "sorry, this page", "このページは存在しません", "404", "ユーザーが見つかりません",
    "该用户不存在", "account doesn't exist", "このアカウントは存在しません",
]


def add(platform, url, label, status, html, extra=None):
    t = title_of(html)
    d = desc_of(html)
    low = ((t or "") + " " + (html or "")[:4000]).lower()
    verdict = "?"
    if status == 404:
        verdict = "无"
    elif status is None:
        verdict = "未取到"
    elif status == 200:
        if any(w in low for w in DEAD_WORDS):
            verdict = "空壳/无"
        else:
            verdict = "有页面"
    elif status in (401, 403, 429):
        verdict = "被挡"
    elif status in (301, 302):
        verdict = "跳转"
    R.append({"platform": platform, "label": label, "url": url,
              "status": status, "title": t, "desc": d,
              "verdict": verdict, "extra": extra})
    note("%-14s %-5s %-8s %s | %s" % (platform, status, verdict, t[:60], url[:70]))
    json.dump(R, open(OUT + "/probe.json", "w"), ensure_ascii=False, indent=1)


H = "ucaliy"

# ---------- 一、按 handle 直探 ----------
SITES = [
    ("Tumblr", "https://ucaliy.tumblr.com/"),
    ("Tumblr(主站)", "https://www.tumblr.com/ucaliy"),
    ("X/Twitter", "https://x.com/ucaliy"),
    ("X(Twitter旧域)", "https://twitter.com/ucaliy"),
    ("Instagram", "https://www.instagram.com/ucaliy/"),
    ("YouTube", "https://www.youtube.com/@ucaliy"),
    ("YouTube(c)", "https://www.youtube.com/c/ucaliy"),
    ("SoundCloud", "https://soundcloud.com/ucaliy"),
    ("note", "https://note.com/ucaliy"),
    ("GitHub", "https://github.com/ucaliy"),
    ("Pinterest", "https://www.pinterest.com/ucaliy/"),
    ("TikTok", "https://www.tiktok.com/@ucaliy"),
    ("Twitch", "https://www.twitch.tv/ucaliy"),
    ("Vimeo", "https://vimeo.com/ucaliy"),
    ("Medium", "https://medium.com/@ucaliy"),
    ("Bandcamp", "https://ucaliy.bandcamp.com/"),
    ("Mixcloud", "https://www.mixcloud.com/ucaliy/"),
    ("Last.fm", "https://www.last.fm/user/ucaliy"),
    ("Steam", "https://steamcommunity.com/id/ucaliy"),
    ("Reddit", "https://www.reddit.com/user/ucaliy/about.json"),
    ("Ameba", "https://ameblo.jp/ucaliy/"),
    ("FC2ブログ", "https://ucaliy.blog.fc2.com/"),
    ("livedoor", "https://ucaliy.livedoor.biz/"),
    ("Pixiv", "https://www.pixiv.net/users/ucaliy"),
    ("ニコニコ", "https://www.nicovideo.jp/user/ucaliy"),
    ("BOOTH", "https://ucaliy.booth.pm/"),
    ("SUZURI", "https://suzuri.jp/ucaliy"),
    ("Threads", "https://www.threads.net/@ucaliy"),
    ("Bluesky", "https://bsky.app/profile/ucaliy.bsky.social"),
    ("Mastodon(mstdn.jp)", "https://mstdn.jp/@ucaliy"),
    ("Misskey.io", "https://misskey.io/@ucaliy"),
    ("Patreon", "https://www.patreon.com/ucaliy"),
    ("Ko-fi", "https://ko-fi.com/ucaliy"),
    ("Behance", "https://www.behance.net/ucaliy"),
    ("Dribbble", "https://dribbble.com/ucaliy"),
    ("About.me", "https://about.me/ucaliy"),
    ("Linktree", "https://linktr.ee/ucaliy"),
    ("WordPress", "https://ucaliy.wordpress.com/"),
    ("Blogger", "https://ucaliy.blogspot.com/"),
    ("Tumblr(旧)", "https://ucaliy.tumblr.com/archive"),
]
for name, u in SITES:
    st, html, hd = fetch(u, timeout=22)
    add(name, u, H, st, html)

json.dump(R, open(OUT + "/probe.json", "w"), ensure_ascii=False, indent=1)

# ---------- 二、账号 API（比 HTML 更确定） ----------
API = [
    ("GitHub API", "https://api.github.com/users/ucaliy"),
    ("Reddit API", "https://www.reddit.com/user/ucaliy/about.json"),
    ("Bluesky resolve", "https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle=ucaliy.bsky.social"),
    ("Misskey API", "https://misskey.io/api/users/show"),
    ("note API", "https://note.com/api/v2/creators/ucaliy"),
    ("SoundCloud API", "https://soundcloud.com/ucaliy"),
]
for name, u in API:
    if name == "Misskey API":
        continue
    st, body, hd = fetch(u, timeout=22, headers={"Accept": "application/json"})
    short = (body or "")[:300].replace("\n", " ")
    R.append({"platform": name, "label": "api", "url": u, "status": st,
              "title": "", "desc": short, "verdict": "api", "extra": None})
    note("%-16s %-5s %s" % (name, st, short[:120]))
    json.dump(R, open(OUT + "/probe.json", "w"), ensure_ascii=False, indent=1)

# misskey 用 POST
try:
    data = json.dumps({"username": "ucaliy"}).encode()
    req = urllib.request.Request("https://misskey.io/api/users/show", data=data,
                                 headers={"User-Agent": UA,
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=22) as r:
        b = r.read(20000).decode("utf-8", "replace")
    note("Misskey POST %s %s" % (r.status, b[:200]))
    R.append({"platform": "Misskey API(POST)", "label": "api", "url": "https://misskey.io/api/users/show",
              "status": r.status, "title": "", "desc": b[:300], "verdict": "api"})
except urllib.error.HTTPError as e:
    b = e.read(20000).decode("utf-8", "replace")
    note("Misskey POST HTTP %d %s" % (e.code, b[:200]))
    R.append({"platform": "Misskey API(POST)", "label": "api", "url": "https://misskey.io/api/users/show",
              "status": e.code, "title": "", "desc": b[:300], "verdict": "api"})
except Exception as e:
    note("Misskey POST ERR %s" % e)

# ---------- 三、搜索引擎 ----------
QUERIES = [
    ("Bing", "https://www.bing.com/search?q=%22ucaliy%22&setlang=en"),
    ("Bing-ja", "https://www.bing.com/search?q=%22ucaliy%22&setlang=ja&cc=jp"),
    ("DuckDuckGo", "https://html.duckduckgo.com/html/?q=%22ucaliy%22"),
    ("Yahoo JP", "https://search.yahoo.co.jp/search?p=%22ucaliy%22"),
    ("Yandex", "https://yandex.com/search/?text=%22ucaliy%22"),
    ("Bing-tumblr", "https://www.bing.com/search?q=%22ucaliy%22+tumblr"),
    ("Bing-withr", "https://www.bing.com/search?q=%22ucaliy%22+%22with+r%22"),
]
for name, u in QUERIES:
    st, html, hd = fetch(u, timeout=25)
    txt = re.sub(r"<script.*?</script>", " ", html or "", flags=re.S)
    txt = re.sub(r"<style.*?</style>", " ", txt, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    R.append({"platform": name, "label": "search", "url": u, "status": st,
              "title": title_of(html), "desc": txt[:1500], "verdict": "search"})
    note("%-12s %-5s len=%d" % (name, st, len(txt)))
    json.dump(R, open(OUT + "/probe.json", "w"), ensure_ascii=False, indent=1)

# ---------- 四、Wayback：ucaliy.tumblr.com 全量 + 域名变体 ----------
def cdx(q, tag, limit=2000):
    st, body, hd = fetch(q, timeout=60)
    rows = []
    if body and body.strip().startswith("["):
        try:
            d = json.loads(body)
            if d and isinstance(d[0], list):
                rows = [dict(zip(d[0], r)) for r in d[1:]]
        except Exception as e:
            note("cdx parse fail %s" % e)
    note("[cdx] %s status=%s rows=%d" % (tag, st, len(rows)))
    json.dump({"tag": tag, "status": st, "count": len(rows), "rows": rows},
              open(OUT + "/cdx_%s.json" % tag, "w"), ensure_ascii=False)
    return rows


cdx("http://web.archive.org/cdx/search/cdx?url=ucaliy.tumblr.com&matchType=domain"
    "&output=json&fl=timestamp,original,statuscode,mimetype&limit=3000", "ucaliy_tumblr")

note("DONE")
