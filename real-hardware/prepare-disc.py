#!/usr/bin/env python3
"""把本机美版 RMGE01 盘镜像复制进本包，生成完整的待拷贝 SD 卡目录。

用法（在本文件所在目录执行）：
    python prepare-disc.py            # 复制
    python prepare-disc.py --check    # 只检查，不复制

注意：会额外占用约 3.3 GB 磁盘。若只想手动拷到 SD 卡，不必运行本脚本，
      直接把镜像复制到 SD:/3ds/SMG-3DS/game.wbfs 即可。
"""
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(HERE, "3ds", "SMG-3DS", "game.wbfs")

CANDIDATES = [
    r"D:\Dowdload\1103\1103 - Super Mario Galaxy (USA) (En,Fr,Es) (Laojiku.com).wbfs",
    r"D:\Dowdload\1103\1103 - Super Mario Galaxy (USA) (En,Fr,Es).wbfs",
]

FAT32_MAX = 4 * 1024 ** 3 - 1
CHECK_ONLY = "--check" in sys.argv


def find_disc():
    for p in CANDIDATES:
        if os.path.isfile(p):
            return p
    return None


def main():
    src = find_disc()
    if not src:
        print("未找到美版镜像。请把 RMGE01 盘镜像放到以下路径之一，")
        print("或手动复制到 3ds/SMG-3DS/game.wbfs：")
        for p in CANDIDATES:
            print("  " + p)
        return 1

    size = os.path.getsize(src)
    with open(src, "rb") as f:
        head = f.read(0x400)
    ids = [m.group().decode("ascii") for m in re.finditer(rb"RMG[A-Z][0-9][0-9]", head)]
    ok_magic = head[:4] == b"WBFS"
    ok_id = "RMGE01" in ids

    print("源镜像 :", src)
    print("大小   : {:,} B = {:.3f} GiB".format(size, size / 1024 ** 3))
    print("WBFS头 :", "OK" if ok_magic else "异常", "| game ID:", ids or "(未在前 1 KiB 找到)")
    print("FAT32  :", "可放" if size < FAT32_MAX else "超限，需要转 RVZ")

    if not (ok_magic and ok_id and size < FAT32_MAX):
        print("校验未通过，已中止。此移植只验证过美版 RMGE01。")
        return 2

    if os.path.exists(DST):
        print("目标已存在，跳过复制:", DST, "({:,} B)".format(os.path.getsize(DST)))
        return 0
    if CHECK_ONLY:
        print("--check 模式，未复制。")
        return 0

    print("复制中（约 3.3 GB，可能需要一两分钟）...")
    t = time.time()
    shutil.copyfile(src, DST)
    print("完成: {:,} B，用时 {:.1f} s".format(os.path.getsize(DST), time.time() - t))
    print("现在可把整个 3ds/ 文件夹拷到 SD 卡根目录。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
