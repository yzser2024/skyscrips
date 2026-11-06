#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第四轮：IG 另一入口、withr17 站点 CDX 全量、搜索引擎第三方案。"""
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request

OUT = "out_an4"
os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, "log.txt"), "w", encoding="utf-8")


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def get(url, headers=None, timeout=45):
    h = {"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            b = r.read()
            return r.status, b.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            b = e.read().decode("utf-8", "replace")
        except Exception:
            b = ""
        return e.code, b
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


res = {}

# ---------- 1. Instagram 另一入口 ----------
IG_APP = "936619743392459"
for u in ["withr", "withr17", "with_r", "yukari", "yunn", "riko", "rico"]:
    key = "ig_api|" + u
    st, txt = get("https://i.instagram.com/api/v1/users/web_profile_info/?username=" + u,
                  {"x-ig-app-id": IG_APP, "Accept": "*/*",
                   "Referer": "https://www.instagram.com/%s/" % u})
    d = {"status": st, "len": len(txt or "")}
    try:
        j = json.loads(txt)
        us = (j.get("data") or {}).get("user") or {}
        d["user"] = {k: us.get(k) for k in
                     ("username", "full_name", "biography", "external_url",
                      "is_private", "is_verified", "id")}
        d["counts"] = us.get("edge_followed_by", {}).get("count")
    except Exception:
        d["head"] = (txt or "")[:160]
    res[key] = d
    log("%-14s %s %s" % (key, st, str(d.get("user") or d.get("head"))[:110]))

# ---------- 2. withr17 站点 CDX 全量 ----------
cdx_urls = [
    ("withr17_music", "music.geocities.jp/withr17*"),
    ("withr17_www", "www.geocities.jp/withr17*"),
    ("withr17_dom", "geocities.jp/withr17*"),
]
for key, pat in cdx_urls:
    q = ("http://web.archive.org/cdx/search/cdx?url=%s&matchType=prefix"
         "&fl=original,timestamp,statuscode,mimetype&collapse=urlkey&limit=400"
         % urllib.parse.quote(pat, safe=""))
    st, txt = get(q, timeout=90)
    rows = []
    if st == 200 and txt.strip():
        for line in txt.strip().splitlines():
            parts = line.split(" ")
            if len(parts) >= 4:
                rows.append(parts[:4])
    res["cdx|" + key] = {"status": st, "count": len(rows), "rows": rows}
    log("cdx %-14s %s count=%d" % (key, st, len(rows)))

# ---------- 3. 搜索引擎：另两家 ----------
queries = [
    '"withr17"',
    '"music.geocities.jp/withr17"',
    '"with r" "ゆん" 作曲',
    '"yunn" "with r" 曲',
    '"rico" "ゆん" 歌',
]
for q in queries:
    for eng, tpl, parser in [
        ("ddg", "https://html.duckduckgo.com/html/?q=%s", "ddg"),
        ("brave", "https://search.brave.com/search?q=%s", "brave"),
        ("mojeek", "https://www.mojeek.com/search?q=%s", "mojeek"),
    ]:
        url = tpl % urllib.parse.quote(q)
        st, txt = get(url, timeout=45)
        hits = []
        if st == 200:
            if parser == "ddg":
                for m in re.finditer(r'result__a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', txt, re.S):
                    hits.append([m.group(1)[:200], re.sub(r"<[^>]+>", "", m.group(2))[:100]])
            elif parser == "brave":
                for m in re.finditer(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', txt, re.S):
                    t = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                    if len(t) > 12:
                        hits.append([m.group(1)[:200], t[:100]])
            else:
                for m in re.finditer(r'<a class="ob"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', txt, re.S):
                    hits.append([m.group(1)[:200], re.sub(r"<[^>]+>", "", m.group(2))[:100]])
        res["sea|%s|%s" % (eng, q)] = {"status": st, "len": len(txt or ""), "hits": hits[:12]}
        log("sea %-6s %-34s %s hits=%d" % (eng, q, st, len(hits)))
        time.sleep(1)

json.dump(res, open(os.path.join(OUT, "anon4.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("DONE")
