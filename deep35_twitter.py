# -*- coding: utf-8 -*-
"""deep-35  推特账号候选探测：CDX + 档案页正文 + twilog/togetter"""
import os, json, re, time, gzip, urllib.request, urllib.error, urllib.parse
import html as H

OUT = "out_deep35"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def note(s):
    print(s); LOG.write(str(s) + "\n"); LOG.flush()


def get(url, timeout=30, ua=UA):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def text_of(b):
    for enc in ("utf-8", "cp932", "euc-jp"):
        try:
            t = b.decode(enc)
            break
        except Exception:
            t = b.decode("utf-8", "replace")
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", H.unescape(t)).strip()


HANDLES = [
    "ucaliy", "oneyunn79", "oneyunn", "oneday79", "oneday",
    "withr79", "withr17", "withr", "amorxxx79", "amorxxx",
    "yukari79", "yukari_oneyunn", "oneyunns", "ones79", "ones_oneyunn",
    "oneyunn79_", "withr_79", "oneyunn7", "yukari_withr",
]

res = {}

# ---------- 1) twitter CDX ----------
for h in HANDLES:
    row = {"handle": h}
    try:
        q = ("http://web.archive.org/cdx/search/cdx?url=twitter.com/%s&matchType=prefix"
             "&output=json&fl=original,timestamp,statuscode&limit=60" % h)
        st, b = get(q, 60)
        rows = json.loads(b.decode("utf-8", "replace")) if b[:1] == b"[" else []
        snaps = [r for r in rows[1:] if r[2] == "200"]
        row["n_snap"] = len(snaps)
        row["first"] = min((r[1] for r in snaps), default=None)
        row["last"] = max((r[1] for r in snaps), default=None)
        note("  twitter/%-16s 200x%-3d %s ~ %s" % (h, len(snaps), row["first"], row["last"]))
        if snaps:
            snaps.sort(key=lambda r: r[1])
            ts, orig = snaps[0][1], snaps[0][0]
            u = "http://web.archive.org/web/%sid_/%s" % (ts, orig)
            try:
                st2, pb = get(u, 40)
                if pb[:2] == b"\x1f\x8b":
                    pb = gzip.decompress(pb)
                open("%s/pages/tw_%s_%s.html" % (OUT, h, ts), "wb").write(pb)
                body = text_of(pb)
                row["title"] = (re.search(r"<title>(.*?)</title>", pb.decode("utf-8", "replace"),
                                          re.S | re.I) or [None, ""])[1].strip()[:120]
                row["text"] = body[:700]
            except Exception as e:
                row["err"] = str(e)[:80]
    except Exception as e:
        row["cdx_err"] = str(e)[:80]
        note("  twitter/%-16s CDX失败 %s" % (h, str(e)[:50]))
    res["twitter:" + h] = row
    time.sleep(0.8)

# ---------- 2) twilog / togetter ----------
for svc, tpl in [("twilog", "https://twilog.org/%s"),
                 ("togetter", "https://togetter.com/user/%s")]:
    for h in HANDLES:
        try:
            st, b = get(tpl % h, 25)
            if st == 200 and len(b) > 2000:
                t = text_of(b)
                bad = ("見つかりません" in t or "存在しません" in t or "not found" in t.lower())
                note("  %-9s %-16s 200 %d bytes%s" % (svc, h, len(b), " (空)" if bad else " ★"))
                res["%s:%s" % (svc, h)] = {"status": 200, "len": len(b), "empty": bad,
                                           "title": (re.search(r"<title>(.*?)</title>", b.decode("utf-8", "replace"),
                                                               re.S | re.I) or [None, ""])[1].strip()[:120]}
            else:
                note("  %-9s %-16s %s" % (svc, h, st))
        except Exception as e:
            pass
        time.sleep(0.5)

json.dump(res, open(OUT + "/probe.json", "w"), ensure_ascii=False, indent=1)
note("== done ==")
LOG.close()
