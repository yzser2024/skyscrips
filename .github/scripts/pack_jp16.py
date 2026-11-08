#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 out_jp16/mp3 下的 mp3 按 9 首一卷打包成 vol1..vol6.zip"""
import glob
import os
import zipfile

files = sorted(glob.glob("out_jp16/mp3/*.mp3"))
print("mp3 count", len(files))
for i in range(6):
    chunk = files[i * 9:(i + 1) * 9]
    if not chunk:
        break
    name = "vol%d.zip" % (i + 1)
    with zipfile.ZipFile(name, "w", zipfile.ZIP_STORED) as z:
        for f in chunk:
            z.write(f, arcname=os.path.relpath(f, "out_jp16"))
    print(name, len(chunk), os.path.getsize(name))
