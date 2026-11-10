#!/usr/bin/env python3
"""重新生成实机安装包的两种 zip。

    python pack-hardware.py           # 轻量版（不含 3.3 GB 镜像，约 9.5 MB）
    python pack-hardware.py --full    # 完整版（含镜像，约 3.3 GiB，ZIP_STORED）

来源目录固定为 smg3ds/real-hardware/。轻量版解压后需运行 prepare-disc.py 补齐镜像。
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(ROOT, "real-hardware")
FULL = "--full" in sys.argv
OUT = os.path.join(ROOT, "SMG-3DS-hardware-FULL.zip" if FULL else "SMG-3DS-hardware.zip")

EXCLUDE_SUFFIX = ("game.wbfs",) if not FULL else ()

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_STORED if FULL else zipfile.ZIP_DEFLATED,
                     compresslevel=None if FULL else 6, allowZip64=True) as z:
    # 空目录 nand/ 也要保留（存档写入位置）
    zi = zipfile.ZipInfo("3ds/SMG-3DS/nand/")
    zi.external_attr = 0o40775 << 16 | 0x10
    z.writestr(zi, b"")
    count = 0
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(EXCLUDE_SUFFIX) or f.endswith(".pyc"):
                continue
            p = os.path.join(root, f)
            arc = os.path.relpath(p, BASE).replace("\\", "/")
            z.write(p, arc)
            count += 1

z = zipfile.ZipFile(OUT)
print("{}: {} files, {:,} bytes ({:.3f} GiB), CRC={}".format(
    os.path.basename(OUT), len(z.infolist()), os.path.getsize(OUT),
    os.path.getsize(OUT) / 1024 ** 3, z.testzip()))
print("entries:", [i.filename for i in z.infolist()])
