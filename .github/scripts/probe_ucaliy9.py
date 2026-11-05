# -*- coding: utf-8 -*-
"""probe9: 交叉验证 @ucaliy 到底在不在（上一轮 200/404 打架）。
多镜像 + 重试；顺便看 withR17 的关注对象是不是さかなぎ諒。
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

OUT = "out_ua9"
os.makedirs(OUT, exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    line = "%s %s" % (time.strftime("%H:%M:%S"), s)
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()


def get(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(400000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read(50000).decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return None, str(e)[:80]


res = {}
MIRRORS = [
    ("fx", "https://api.fxtwitter.com/%s"),
    ("vx", "https://api.vxtwitter.com/%s"),
    ("fx2", "https://api.fxtwitter.com/2/profile/%s"),
]
for rnd in range(3):
    for n in ["ucaliy", "withR17"]:
        for tag, tpl in MIRRORS:
            u = tpl % n
            st, b = get(u)
            key = "%s|%s|r%d" % (tag, n, rnd)
            brief = (b or "")[:200].replace("\n", " ")
            res[key] = {"status": st, "body": (b or "")[:2000]}
            note("%-16s %-4s %s" % (key, st, brief[:150]))
            time.sleep(2)
    time.sleep(6)

json.dump(res, open(OUT + "/mirrors.json", "w"), ensure_ascii=False, indent=1)

# withR17 的关注列表（若镜像支持）
for u in ["https://api.fxtwitter.com/withR17/following",
          "https://api.vxtwitter.com/withR17/following"]:
    st, b = get(u)
    note("following %-46s %s %s" % (u, st, (b or "")[:200].replace("\n", " ")))
    res["follow_" + u.split("//")[1][:20]] = {"status": st, "body": (b or "")[:1500]}
    time.sleep(3)

# syndication 时间线页（含用户卡）
for n in ["withR17", "ucaliy"]:
    u = "https://syndication.twitter.com/srv/timeline-profile/screen-name/" + n
    st, b = get(u, timeout=30)
    t = re.sub(r"<script.*?</script>", " ", b or "", flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    note("synd %-10s %s len=%d | %s" % (n, st, len(b or ""), t[:200]))
    res["synd_" + n] = {"status": st, "len": len(b or ""), "text": t[:800]}
    time.sleep(4)

json.dump(res, open(OUT + "/mirrors.json", "w"), ensure_ascii=False, indent=1)
note("DONE")
