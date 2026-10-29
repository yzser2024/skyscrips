# -*- coding: utf-8 -*-
"""deep-50: SoundCloud「With R」18 首曲目的完整描述（Behind this track）
- 逐一调 api-v2 /tracks/<id> 取完整 description / tag_list / caption
- 同时抓网页 HTML，比对 hydration 中的 description，确认 App 端「Show more」是否藏了内容
- 附带抓每首曲下的听众评论
"""
import os, re, json, time, urllib.request, urllib.error

OUT = "out_deep50"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

IDS = [177151629, 177151632, 177151633, 177151636, 177151642, 177151639,
       177151646, 177151644, 177151648, 177151650, 177151658, 177151663,
       177151664, 177151668, 177151665, 177151669, 177152685, 191600238]
PERMA = ["z5ufjbsqiif4", "caq21iqublhj", "core", "vuanbr3bsatr", "irodori", "glace",
         "h3j3qiydfh9y", "iqrteo9uhkoz", "in-my-shade", "vuep40blpwt6", "crezfs05dk4c",
         "5wjuiiwmngym", "awlp3x7h9qsy", "wherever-she-goes", "songbird", "final-tale",
         "forgery-1", "gloomy-days"]


def note(s):
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def get(url, tries=5, timeout=45):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                note("    %d retry %d" % (e.code, i + 1))
                time.sleep(10 + i * 15)
                continue
            note("    HTTP %d %s" % (e.code, url[:90]))
            return e.code, ""
        except Exception as e:
            note("    ERR %s" % str(e)[:70])
            time.sleep(5 + i * 8)
    return None, ""


st, h = get("https://soundcloud.com/withr")
m = re.search(r'window\.__sc_hydration\s*=\s*(\[.*?\]);', h or "", re.S)
data = json.loads(m.group(1)) if m else []
client = None
for x in data:
    if x.get("hydratable") == "apiClient":
        client = x["data"].get("id")
note("client_id=%s" % client)
if not client:
    note("无 client_id，结束")
    raise SystemExit

tracks = []
comments = []
for idx, (tid, pk) in enumerate(zip(IDS, PERMA), 1):
    note("== %d/%d id=%s %s" % (idx, len(IDS), tid, pk))
    # 1) 网页（含 hydration 里的 track 对象）
    st, html = get("https://soundcloud.com/withr/" + pk)
    if st == 200 and html:
        open(OUT + "/pages/%s_%s.html" % (pk, tid), "w", encoding="utf-8").write(html)
        hm = re.search(r'window\.__sc_hydration\s*=\s*(\[.*?\]);', html, re.S)
        if hm:
            try:
                for blk in json.loads(hm.group(1)):
                    d = blk.get("data") or {}
                    if isinstance(d, dict) and d.get("id") == tid and d.get("kind") == "track":
                        note("    网页 description len=%d" % len(d.get("description") or ""))
                        break
            except Exception as e:
                note("    hyd 解析失败 %s" % str(e)[:40])
        note("    HTML %d bytes" % len(html))
    else:
        note("    网页 %s" % st)
    time.sleep(1.5)

    # 2) api-v2 完整 track
    st, t = get("https://api-v2.soundcloud.com/tracks/%d?client_id=%s" % (tid, client))
    if t:
        try:
            tr = json.loads(t)
            tr.pop("user", None)
            tr.pop("media", None)
            tr.pop("visuals", None)
            tracks.append(tr)
            note("    API description len=%d tags=%r cap=%r" %
                 (len(tr.get("description") or ""), tr.get("tag_list"), tr.get("caption")))
        except Exception as e:
            note("    API 解析失败 %s" % str(e)[:50])
    else:
        note("    API 空")

    # 3) 评论
    st, c = get("https://api-v2.soundcloud.com/tracks/%d/comments?client_id=%s&limit=50&threaded=0" % (tid, client))
    if c:
        try:
            cc = json.loads(c).get("collection", [])
            for x in cc:
                comments.append({"track_id": tid, "track": pk, "created_at": x.get("created_at"),
                                 "body": x.get("body"), "user": (x.get("user") or {}).get("username"),
                                 "ts": x.get("timestamp")})
            note("    评论 %d" % len(cc))
        except Exception as e:
            note("    评论解析失败 %s" % str(e)[:40])
    time.sleep(1.5)

json.dump(tracks, open(OUT + "/tracks_full.json", "w"), ensure_ascii=False, indent=1)
json.dump(comments, open(OUT + "/comments.json", "w"), ensure_ascii=False, indent=1)
note("done tracks=%d comments=%d" % (len(tracks), len(comments)))
