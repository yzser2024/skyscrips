# -*- coding: utf-8 -*-
"""deep-42: 推特 @ucaliy 第三方存档直连抢救（2010-2016）
twilog 是日本最大的推文全存档服务，账号注销后其存档通常仍在。
1) 直连探测 twilog / twpro / togetter / archive.today
2) twilog 若存在则按 page-N 与 date-YYMM 全量抓取
"""
import os, re, json, time, urllib.request, urllib.error, random, gzip, io

OUT = "out_deep42"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def fetch(url, tries=3, timeout=45, ref=None):
    h = {"User-Agent": UA, "Accept-Language": "ja,en;q=0.8",
         "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
    if ref:
        h["Referer"] = ref
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                if b[:2] == b"\x1f\x8b":
                    try:
                        b = gzip.decompress(b)
                    except Exception:
                        pass
                return r.status, b
        except urllib.error.HTTPError as e:
            note("    HTTP %d %s" % (e.code, url[:80]))
            if e.code in (429, 503, 502, 504):
                time.sleep(10 + i * 12)
                continue
            return e.code, b""
        except Exception as e:
            note("    ERR %s %s" % (str(e)[:60], url[:70]))
            time.sleep(6 + i * 8)
    return None, b""


PROBES = [
    "https://twilog.org/ucaliy",
    "https://twilog.org/ucaliy/stats",
    "https://twilog.org/ucaliy/date-1008",
    "https://twpro.jp/ucaliy",
    "https://togetter.com/search?q=ucaliy",
    "https://archive.ph/newest/https://twitter.com/ucaliy",
    "https://web.archive.org/web/2012/http://twitter.com/ucaliy",
]

probe = {}
for u in PROBES:
    st, b = fetch(u)
    probe[u] = {"status": st, "size": len(b)}
    note("PROBE %-55s %s %d" % (u[:55], st, len(b)))
    if st == 200 and b:
        fn = "%s/pages/probe_%s.html" % (OUT, re.sub(r"[^a-zA-Z0-9]", "_", u)[-60:])
        open(fn, "wb").write(b)
    time.sleep(2)

json.dump(probe, open(OUT + "/probe.json", "w"), ensure_ascii=False, indent=1)

# ---- twilog 全量 ----
st, home = fetch("https://twilog.org/ucaliy")
if st != 200 or len(home) < 1000:
    note("twilog 首页不可用，结束")
    note("done")
    raise SystemExit

txt = home.decode("utf-8", "replace")
open(OUT + "/pages/twilog_home.html", "wb").write(home)
note("twilog 首页 %d bytes" % len(home))
# 标题/简介
mt = re.search(r"<title>(.*?)</title>", txt, re.S)
if mt:
    note("  title: " + mt.group(1).strip()[:120])

# 找出所有 date-YYMM 链接
months = sorted(set(re.findall(r"/ucaliy/date-(\d{4})", txt)))
note("  月份链接: %s" % ",".join(months[:60]))
pages = sorted(set(re.findall(r"/ucaliy/page-(\d+)", txt)), key=lambda x: int(x))
maxpage = max([int(p) for p in pages], default=1)
note("  最大页码线索: %d" % maxpage)

manifest = []


def save(url, name):
    st, b = fetch(url, ref="https://twilog.org/ucaliy")
    if st == 200 and len(b) > 800:
        open("%s/pages/%s.html" % (OUT, name), "wb").write(b)
        note("  OK %s %d" % (name, len(b)))
        manifest.append({"url": url, "file": name + ".html", "size": len(b)})
        return b
    note("  -- %s %s" % (name, st))
    return None


# 月份页（最多 60）
for m in months[:60]:
    save("https://twilog.org/ucaliy/date-%s" % m, "date_%s" % m)
    time.sleep(1.5 + random.random() * 1.5)

# 分页（推到 200 页，遇到空就停）
empty = 0
for p in range(2, 201):
    b = save("https://twilog.org/ucaliy/page-%d" % p, "page_%03d" % p)
    if b is None:
        empty += 1
        if empty >= 3:
            note("  连续 3 页失败，停止分页")
            break
    else:
        empty = 0
    time.sleep(1.2 + random.random() * 1.5)

json.dump(manifest, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done %d pages" % len(manifest))
