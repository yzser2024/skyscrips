#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deep27: 把 Wayback 里 651 板的存档 URL 全部挖出来（CDX 多次重试）。"""
import gzip
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_deep27"
os.makedirs(OUT, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
log = []


def note(s):
    print(s, flush=True)
    log.append(s)


def get(url, timeout=60, tries=6):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "application/json,*/*"})
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                b = r.read()
            if b[:2] == b"\x1f\x8b":
                try:
                    b = gzip.decompress(b)
                except Exception:
                    pass
            return b
        except urllib.error.HTTPError as e:
            last = "HTTP %s" % e.code
            if e.code in (429, 503, 502, 504):
                time.sleep(8 + i * 6)
                continue
            raise
        except Exception as e:
            last = str(e)[:60]
            time.sleep(5 + i * 4)
    raise RuntimeError(last or "fail")


QUERIES = [
    ("651-all", "http://web.archive.org/cdx/search/cdx?url=www5.rocketbbs.com/651"
                "&matchType=prefix&fl=original,timestamp,statuscode,mimetype,length"
                "&collapse=urlkey&limit=2000&output=json"),
    ("651-nofold", "http://web.archive.org/cdx/search/cdx?url=www5.rocketbbs.com/651"
                   "&matchType=prefix&fl=original,timestamp,statuscode,length"
                   "&limit=3000&output=json"),
    ("oneday-nofold", "http://web.archive.org/cdx/search/cdx?url=www5.rocketbbs.com/651/oneday.html"
                      "&fl=timestamp,statuscode,length,digest&limit=500&output=json"),
    ("bbs-oneday", "http://web.archive.org/cdx/search/cdx?url=www5.rocketbbs.com/651/bbs.cgi"
                   "&matchType=prefix&fl=original,timestamp,statuscode,length"
                   "&limit=2000&output=json"),
    ("other-mirror", "http://web.archive.org/cdx/search/cdx?url=rocketbbs.com/651"
                     "&matchType=prefix&fl=original,timestamp,statuscode&collapse=urlkey"
                     "&limit=500&output=json"),
]

for tag, u in QUERIES:
    try:
        b = get(u)
        rows = json.loads(b)
        note("== %-14s %d 行" % (tag, max(0, len(rows) - 1)))
        json.dump(rows, open("%s/%s.json" % (OUT, tag), "w"),
                  ensure_ascii=False, indent=1)
        for r in rows[1:81]:
            note("   " + "  ".join(str(x) for x in r))
        if len(rows) > 81:
            note("   … 共 %d 行，见 json" % (len(rows) - 1))
    except Exception as e:
        note("== %-14s FAIL %s" % (tag, str(e)[:100]))
    time.sleep(3)

open(OUT + "/log.txt", "w", encoding="utf-8").write("\n".join(log))
