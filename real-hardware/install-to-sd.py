#!/usr/bin/env python3
"""把本包一次性拷到 SD 卡，做成插卡即用的状态。

用法（在本文件所在目录执行）：
    py -3 install-to-sd.py --list        # 列出本机盘符/类型，找 SD 卡
    py -3 install-to-sd.py E: --dry-run  # 预览会做什么，不写
    py -3 install-to-sd.py E:            # 实际拷贝

会做三件事（不会删除 SD 卡上任何其它文件）：
  1. 本包 3ds/  ->  <SD 卡>\\3ds\\           （含 3.268 GiB 的 game.wbfs）
  2. cia/SMG-3DS.cia -> <SD 卡>\\cia\\SMG-3DS.cia
  3. 校验目标文件、打印后续步骤

SD 卡需 FAT32（3DS 不认 exFAT/NTFS），剩余空间 >= 4 GiB。
"""
import ctypes
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_3DS = os.path.join(HERE, "3ds")
SRC_CIA = os.path.join(HERE, "cia", "SMG-3DS.cia")
DISC = os.path.join(SRC_3DS, "SMG-3DS", "game.wbfs")
FAT32_MAX = 4 * 1024 ** 3 - 1


def list_drives():
    """列出逻辑盘符及类型，帮助定位 SD 卡。"""
    kernel32 = ctypes.windll.kernel32
    bitmask = kernel32.GetLogicalDrives()
    types = {0: "未知", 1: "无根目录", 2: "可移动", 3: "本地磁盘",
             4: "网络", 5: "光驱", 6: "RAM 盘"}
    print("本机盘符：")
    for i in range(26):
        if not (bitmask >> i) & 1:
            continue
        root = "{}:\\".format(chr(ord("A") + i))
        t = kernel32.GetDriveTypeW(root)
        free = ""
        try:
            free = "{:.1f} GiB 可用".format(shutil.disk_usage(root).free / 1024 ** 3)
        except OSError:
            pass
        print("  {}  {:<8} {}".format(root, types.get(t, "?"), free))
    print("\nSD 卡一般是「可移动」，且不应该是 C:")


def verify_disc():
    if not os.path.isfile(DISC):
        print("缺少盘镜像:", DISC)
        print("先运行 `python prepare-disc.py` 把美版镜像复制进本包。")
        return False
    size = os.path.getsize(DISC)
    with open(DISC, "rb") as f:
        head = f.read(0x400)
    ids = [m.group().decode("ascii") for m in re.finditer(rb"RMG[A-Z][0-9][0-9]", head)]
    ok = head[:4] == b"WBFS" and "RMGE01" in ids and size < FAT32_MAX
    print("盘镜像: {:,} B = {:.3f} GiB | WBFS={} | ID={} | FAT32 可放={}".format(
        size, size / 1024 ** 3, head[:4], ids or "?", size < FAT32_MAX))
    if not ok:
        print("校验失败：必须是美版 RMGE01 且小于 4 GiB。日版汉化盘实测卡在 boot。")
    return ok


def copy_tree(src, dst, dry):
    """合并式复制，不删除目标上已有的其它文件。"""
    n = 0
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target = dst if rel == "." else os.path.join(dst, rel)
        if not dry:
            os.makedirs(target, exist_ok=True)
        for f in files:
            s = os.path.join(root, f)
            d = os.path.join(target, f)
            relp = os.path.relpath(d, dst)
            exists = os.path.exists(d)
            print("  {} {} ({:,} B)".format("覆盖" if exists else "新建", relp, os.path.getsize(s)))
            if not dry:
                shutil.copy2(s, d)
            n += 1
    return n


def main():
    args = [a for a in sys.argv[1:]]
    if "--list" in args or not args:
        list_drives()
        if not args:
            print("\n用法: py -3 install-to-sd.py <盘符> [--dry-run]")
        return 0

    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    dest = args[0]
    if len(dest) == 2 and dest[1] == ":":
        dest += "\\"
    if not os.path.isdir(dest):
        print("目标不存在或不是目录:", dest)
        return 1
    if os.path.abspath(dest).upper().startswith("C:\\"):
        print("拒绝写入 C: —— 请明确指定 SD 卡盘符。")
        return 1

    print("目标:", os.path.abspath(dest))
    print("模式:", "预览（不写）" if dry else "实际拷贝")
    free = shutil.disk_usage(dest).free
    print("剩余空间: {:.1f} GiB".format(free / 1024 ** 3))
    if free < FAT32_MAX + 64 * 1024 ** 2:
        print("空间不足，至少需要约 4 GiB。")
        return 1

    if not verify_disc():
        return 2
    if not os.path.isfile(SRC_CIA):
        print("缺少 CIA:", SRC_CIA)
        return 2

    t = time.time()
    print("\n[1/2] 复制 3ds/ ->", os.path.join(dest, "3ds"))
    n = copy_tree(SRC_3DS, os.path.join(dest, "3ds"), dry)
    print("[2/2] 复制 CIA ->", os.path.join(dest, "cia", "SMG-3DS.cia"))
    if not dry:
        os.makedirs(os.path.join(dest, "cia"), exist_ok=True)
        shutil.copy2(SRC_CIA, os.path.join(dest, "cia", "SMG-3DS.cia"))
    print("  cia/SMG-3DS.cia ({:,} B)".format(os.path.getsize(SRC_CIA)))
    print("\n共 {} 个文件，用时 {:.1f} s".format(n + 1, time.time() - t))

    if dry:
        print("预览结束，未写入任何文件。去掉 --dry-run 即可实际执行。")
        return 0

    ok = True
    for rel, expected in [
        ("3ds/SMG-3DS/game.wbfs", os.path.getsize(DISC)),
        ("3ds/SMG-3DS/SMG-3DS.3dsx", os.path.getsize(os.path.join(SRC_3DS, "SMG-3DS", "SMG-3DS.3dsx"))),
        ("3ds/dspfirm.cdc", os.path.getsize(os.path.join(SRC_3DS, "dspfirm.cdc"))),
        ("cia/SMG-3DS.cia", os.path.getsize(SRC_CIA)),
    ]:
        p = os.path.join(dest, rel.replace("/", os.sep))
        good = os.path.isfile(p) and os.path.getsize(p) == expected
        print("  校验 {:<38} {}".format(rel, "OK" if good else "失败"))
        ok &= good

    print("\n完成。接下来：")
    print("  1. 确认 SD 卡是 FAT32（3DS 不认 exFAT/NTFS）。")
    print("  2. 插卡开机，用 FBI / GodMode9 安装 SD:\\cia\\SMG-3DS.cia（需 Luma3DS）。")
    print("  3. HOME 菜单点 SMG-3DS 启动；或不用 CIA，走 Homebrew Launcher 启动 3dsx 原版。")
    print("  4. 标题处按 A + R；游戏资源全部来自 SD:\\3ds\\SMG-3DS\\，别删这个目录。")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
