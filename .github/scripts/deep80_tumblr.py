import json, os, hashlib, urllib.request, urllib.error, time

URL = "https://a.tumblr.com/tumblr_nt2ry9NaVF1udjnj8o1.mp3"
OUT = "out_deep80"
os.makedirs(OUT, exist_ok=True)

info = {"url": URL}
# 先 HEAD
for method in ("HEAD", "GET"):
    try:
        req = urllib.request.Request(URL, method=method,
                                     headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
        r = urllib.request.urlopen(req, timeout=60)
        info[method + "_status"] = r.status
        info[method + "_headers"] = {k.lower(): v for k, v in r.headers.items()}
        if method == "GET":
            data = r.read()
            info["bytes"] = len(data)
            info["md5"] = hashlib.md5(data).hexdigest()
            info["head_hex"] = data[:16].hex()
            info["tail_hex"] = data[-16:].hex()
            open(os.path.join(OUT, "tumblr_nt2ry9NaVF1udjnj8o1.mp3"), "wb").write(data)
        r.close()
        break
    except Exception as e:
        info[method + "_error"] = "%s: %s" % (type(e).__name__, e)
    time.sleep(2)

# 顺便取帖子页面（若能开）
for u in ["https://ucaliy.tumblr.com/post/126669799930",
          "http://ucaliy.tumblr.com/post/126669799930/scarecrow-in-the-isolated-island-i-created-this"]:
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        r = urllib.request.urlopen(req, timeout=60)
        body = r.read()
        info["post_" + u.split("/")[2]] = {"status": r.status, "bytes": len(body)}
        open(os.path.join(OUT, "post_%d.html" % len(info)), "wb").write(body)
        r.close()
    except Exception as e:
        info["post_error_" + u.split("/")[2]] = "%s: %s" % (type(e).__name__, e)

# 封面图
COVER = "https://64.media.tumblr.com/tumblr_nt2ry9NaVF1udjnj8o1_1439560450_cover.jpg"
try:
    req = urllib.request.Request(COVER, headers={"User-Agent": "Mozilla/5.0"})
    r = urllib.request.urlopen(req, timeout=60)
    cb = r.read()
    info["cover"] = {"status": r.status, "bytes": len(cb), "md5": hashlib.md5(cb).hexdigest()}
    open(os.path.join(OUT, "cover.jpg"), "wb").write(cb)
    r.close()
except Exception as e:
    info["cover_error"] = "%s: %s" % (type(e).__name__, e)

json.dump(info, open(os.path.join(OUT, "result.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(info, ensure_ascii=False, indent=1)[:3000])
