#!/usr/bin/env python3
"""解析 note-sound 89 首的 play_url（仅需文本，超小产物）。"""
import os, json, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SOUNDS = json.load(open(os.path.join(HERE, "sounds.json"), encoding="utf-8"))
os.makedirs("out_jp25", exist_ok=True)

out = []
for i, item in enumerate(SOUNDS):
    name, sid = item[0], item[1]
    rec = {"idx": i, "name": name, "sound_id": sid}
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                "https://note.com/api/v3/sounds/" + sid,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
                    "Referer": "https://note.com/",
                    "Accept": "application/json",
                },
            )
            d = json.load(urllib.request.urlopen(req, timeout=25))["data"]
            rec.update({
                "title": d.get("title"),
                "original_filename": d.get("original_filename"),
                "duration": d.get("duration"),
                "downloadable": d.get("downloadable"),
                "play_url": d.get("play_url"),
            })
            break
        except Exception as e:
            rec["err"] = "%s: %s" % (type(e).__name__, str(e)[:60])
            time.sleep(1.5)
    out.append(rec)
    if i % 20 == 0:
        print("progress", i, flush=True)

json.dump(out, open("out_jp25/play_urls.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
ok = sum(1 for x in out if x.get("play_url"))
print("RESOLVED %d / %d" % (ok, len(out)), flush=True)
