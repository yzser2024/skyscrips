# -*- coding: utf-8 -*-
"""probe5: 核实 CDX 里两条「前缀误匹配」的账号是不是她。
 - twitter.com/UCaliyo  ≠ ucaliy（大小写模糊匹配）
 - instagram.com/ucaliy17 ≠ ucaliy（前缀匹配，但 17 是她的站名后缀，需查）
另外把 ucaliy 的各种常见变体在 CDX 里过一遍。
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_ua5"
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


def get(url, timeout=45):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "ja,en;q=0.8"}
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(800000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read(200000).decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return None, str(e)[:80]


def add(tag, url, status, body, extra=""):
    R.append({"tag": tag, "url": url, "status": status,
              "body": (body or "")[:1500], "extra": extra})
    note("%-24s %-5s %s" % (tag, status, extra[:130]))
    json.dump(R, open(OUT + "/probe5.json", "w"), ensure_ascii=False, indent=1)


def textof(html):
    t = re.sub(r"<script.*?</script>", " ", html or "", flags=re.S)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# 1. UCaliyo 的一条推文（判断是不是同一个人）
u = "http://web.archive.org/web/20210224042032/https://twitter.com/UCaliyo/status/1364429856256188417"
st, b = get(u)
t = textof(b)
add("UCaliyo 推文", u, st, b, "text=" + t[:200])

time.sleep(12)

# 2. instagram ucaliy17 的存档
u = "http://web.archive.org/web/20201101235223/https://www.instagram.com/ucaliy17/"
st, b = get(u)
og = re.search(r'property=["\']og:description["\'][^>]+content=["\'](.*?)["\']', b or "", re.S)
ti = re.search(r'property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', b or "", re.S)
add("IG ucaliy17 存档", u, st, b,
    "og:title=%s | og:desc=%s | len=%d" % ((ti.group(1) if ti else "")[:80],
                                           (og.group(1) if og else "")[:200], len(b or "")))

time.sleep(12)

# 3. 现存地址再探一次（第一轮 429）
for tag, u in [("IG ucaliy17 现址", "https://www.instagram.com/ucaliy17/"),
               ("X ucaliy 现址", "https://x.com/ucaliy"),
               ("X ucaliyo 现址", "https://x.com/UCaliyo")]:
    st, b = get(u, timeout=30)
    add(tag, u, st, b, "len=%d" % len(b or ""))
    time.sleep(3)


# 4. CDX 扫变体
def cdx(q, tag):
    st, b = get(q, timeout=55)
    rows = []
    if b and b.strip().startswith("["):
        try:
            d = json.loads(b)
            if d and isinstance(d[0], list):
                rows = [dict(zip(d[0], r)) for r in d[1:]]
        except Exception:
            pass
    json.dump({"tag": tag, "status": st, "count": len(rows), "rows": rows},
              open(OUT + "/cdx_%s.json" % tag, "w"), ensure_ascii=False)
    note("[cdx] %-16s %s rows=%d" % (tag, st, len(rows)))
    for r in rows[:6]:
        note("        %s %s" % (r["timestamp"], r["original"][:80]))
    return rows


BASE = ("http://web.archive.org/cdx/search/cdx?url=%s&matchType=prefix"
        "&output=json&fl=timestamp,original,statuscode&limit=400")

for prec, tag in [
    ("instagram.com/ucaliy17", "ig17"),
    ("twitter.com/ucaliyo", "tw_ucaliyo"),
    ("instagram.com/ucaliy_", "ig_us"),
    ("ucaliy.tumblr.com", "tb"),
]:
    cdx(BASE % urllib.parse.quote(prec, safe=""), tag)
    time.sleep(8)

note("DONE")
