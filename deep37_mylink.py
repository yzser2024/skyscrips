# -*- coding: utf-8 -*-
"""deep-37  死磕 mylink.html / link.html（含 429 退避重试与多时间戳兜底）"""
import os, json, re, time, gzip, urllib.request, urllib.error, html as H
import urllib.parse

OUT = "out_deep37"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def note(s):
    print(s); LOG.write(str(s) + "\n"); LOG.flush()


def get(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def fetch_soft(url, tries=6):
    """429/503 时指数退避"""
    for k in range(tries):
        try:
            st, b = get(url)
            if b[:2] == b"\x1f\x8b":
                b = gzip.decompress(b)
            return b
        except urllib.error.HTTPError as e:
            wait = 20 + k * 25
            note("      %s -> %s, 等 %ds" % (url.split("/web/")[-1][:60], e.code, wait))
            time.sleep(wait)
        except Exception as e:
            note("      err %s" % str(e)[:60])
            time.sleep(12 + k * 10)
    return None


def cdx(url):
    q = ("http://web.archive.org/cdx/search/cdx?url=%s&output=json"
         "&fl=original,timestamp,statuscode&limit=200" % urllib.parse.quote(url, safe=""))
    b = fetch_soft(q, 4)
    try:
        return json.loads(b.decode("utf-8", "replace")) if b and b[:1] == b"[" else []
    except Exception:
        return []


def show(name, b):
    if not b:
        note("== %s  取不到" % name)
        return
    open("%s/pages/%s" % (OUT, name), "wb").write(b)
    t = b.decode("cp932", "replace")
    body = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
    body = re.sub(r"<br\s*/?>", "\n", body, flags=re.I)
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"[ \t\u3000]+", " ", H.unescape(body))
    body = re.sub(r"\n\s*\n+", "\n", body).strip()
    note("== %s  %d bytes / 正文 %d 字" % (name, len(b), len(body)))
    note(body[:1200])
    links = re.findall(r'(?:href|src)="([^"]+)"', t, re.I)
    ext = sorted({x for x in links if x.lower().startswith("http")
                  and "geocities" not in x and "rocketbbs" not in x})
    note("  --- 站外链接 %d 条 ---" % len(ext))
    for x in ext:
        note("     " + x)


# ---- 1) 先查 mylink/link 各自有哪些快照 ----
for path in ["mylink.html", "link.html", "link2.html", "bbs.html", "profile.html"]:
    u = "http://www.geocities.jp/amorxxx79/" + path
    rows = cdx(u)
    snaps = [r for r in rows[1:] if r[2] == "200"] if len(rows) > 1 else []
    note("CDX %-14s %d 条 200  %s" % (path, len(snaps),
         ", ".join(r[1] for r in snaps[:6])))
    for r in snaps[:3]:
        b = fetch_soft("http://web.archive.org/web/%sid_/%s" % (r[1], r[0]), 5)
        show("%s__%s" % (path, r[1]), b)
        if b:
            break
    time.sleep(10)

LOG.close()
