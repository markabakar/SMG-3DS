#!/usr/bin/env python3
"""在 SD 卡上切换 3dsx：诊断版 / 强制英语修复版 / 帧率显示版 / 恢复官方原版。

    py -3 install-diag.py --list           列出盘符
    py -3 install-diag.py F: --dry-run     预览，不写
    py -3 install-diag.py F:              ★ 安装诊断版（把崩溃原因写 boot-log.txt）
    py -3 install-diag.py F: --english    ★★ 安装「强制英语修复版」(推荐先看 ROOT-CAUSE.txt)
    py -3 install-diag.py F: --fps        ★★★ 帧率显示版（英语修复 + 下屏 FPS，日常推荐）
    py -3 install-diag.py F: --clipfix    ★ 实验：2D/JPA 条纹也走 CPU 近平面裁剪（真机未验证）
    py -3 install-diag.py F: --restore     恢复官方原版

脚本只碰这一个文件：SD:/3ds/SMG-3DS/SMG-3DS.3dsx
用包内的官方原版建立 SMG-3DS.3dsx.stock 备份（--restore 一定回到官方原版）；
若卡上当前不是官方原版，会额外另存为 SMG-3DS.3dsx.previous，不丢文件。
不会删 game.wbfs / settings.ini；会清掉上一次的 boot-log.txt 避免拿到旧日志。
"""
import ctypes
import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIAG = os.path.join(HERE, "optional", "SMG-3DS-diag.3dsx")
ENGLISH = os.path.join(HERE, "optional", "SMG-3DS-english.3dsx")
FPS = os.path.join(HERE, "optional", "SMG-3DS-fps.3dsx")
CLIPFIX = os.path.join(HERE, "optional", "SMG-3DS-clipfix.3dsx")
STOCK = os.path.join(HERE, "3ds", "SMG-3DS", "SMG-3DS.3dsx")
DIAG_SHA = "a34b998e70b5d18efd65ee2c1b89afa7e8852a6006cf1e4ae8610fdecf83140a"
ENGLISH_SHA = "5c13c3b7796766ef73dae2782136f5bdc37d37b4113eafe114b191fbda6128fa"
FPS_SHA = "337fd25ed66f315211fe57ba802e5990d67d5c2b9f6a4cbebe6c19ecea2c24c7"
CLIPFIX_SHA = "d64891a0d2972576b07bb33dd0bc6b77a1b8ac14158da48d5d7327778a25fb9b"


def list_drives():
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    types = {0: "未知", 1: "无根目录", 2: "可移动", 3: "本地磁盘", 4: "网络", 5: "光驱", 6: "RAM盘"}
    print("本机盘符：")
    for i in range(26):
        if not (bitmask >> i) & 1:
            continue
        root = "{}:\\".format(chr(ord("A") + i))
        t = ctypes.windll.kernel32.GetDriveTypeW(root)
        free = ""
        try:
            free = "{:.1f} GiB 可用".format(shutil.disk_usage(root).free / 1024 ** 3)
        except OSError:
            pass
        print("  {}  {:<8} {}".format(root, types.get(t, "?"), free))
    print("SD 卡一般是「可移动」，且不应该是 C:")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    args = list(sys.argv[1:])
    if "--list" in args or not args:
        list_drives()
        if not args:
            print("\n用法: py -3 install-diag.py <盘符> [--english | --restore | --dry-run]")
        return 0

    dry = "--dry-run" in args
    restore = "--restore" in args
    english = "--english" in args
    fps = "--fps" in args
    clipfix = "--clipfix" in args
    if fps or clipfix:
        english = False
    if clipfix:
        fps = False
    args = [a for a in args if a not in ("--dry-run", "--restore", "--english", "--fps", "--clipfix")]
    dest = args[0]
    if len(dest) == 2 and dest[1] == ":":
        dest += "\\"
    if not os.path.isdir(dest):
        print("目标不存在:", dest)
        return 1
    if os.path.abspath(dest).upper().startswith("C:\\"):
        print("拒绝写 C:，请指定 SD 卡盘符。")
        return 1

    app = os.path.join(dest, "3ds", "SMG-3DS")
    target = os.path.join(app, "SMG-3DS.3dsx")
    backup = target + ".stock"
    log = os.path.join(app, "boot-log.txt")
    mode = "预览" if dry else ("恢复原版" if restore else
                              ("安装实验裁剪版" if clipfix else
                               ("安装帧率显示版" if fps else
                               ("安装强制英语修复版" if english else "安装诊断版"))))
    print("SD 卡:", os.path.abspath(dest))
    print("模式:", mode)

    if not os.path.isdir(app):
        print("找不到", app, "—— 请先把本包的 3ds/ 拷到 SD 卡根（可先跑 install-to-sd.py）")
        return 1
    if not os.path.isfile(target):
        print("找不到", target)
        return 1
    print("当前 3dsx:", os.path.getsize(target), "B")

    if restore:
        if not os.path.isfile(backup):
            print("没有备份", backup, "——可直接从本包 3ds/SMG-3DS/SMG-3DS.3dsx 再拷一次")
            return 1
        print("恢复:", os.path.basename(backup), "->", "SMG-3DS.3dsx")
        if not dry:
            shutil.copy2(backup, target)
            if os.path.isfile(log):
                os.remove(log)
        print("完成，官方原版已恢复。")
        return 0

    source = CLIPFIX if clipfix else (FPS if fps else (ENGLISH if english else DIAG))
    expected = CLIPFIX_SHA if clipfix else (FPS_SHA if fps else (ENGLISH_SHA if english else DIAG_SHA))
    label = "实验裁剪版" if clipfix else ("帧率显示版" if fps else ("修复版" if english else "诊断版"))
    if not os.path.isfile(source):
        print("缺少" + label + ":", source)
        return 1
    source_hash = sha(source)
    print(label + " SHA-256:", source_hash[:16], "...", "OK" if source_hash == expected else "与预期不符（仍可使用）")

    if not os.path.isfile(backup):
        # The card may already hold the DIAG build (e.g. after a previous run).
        # Backing up "whatever is there" would make --restore bring back the diag
        # build instead of the official one. Always seed .stock from the package's
        # official build, and keep the current file aside as .previous.
        if not os.path.isfile(STOCK):
            print("缺少包内官方原版:", STOCK)
            return 1
        if sha(target) != sha(STOCK):
            prev = target + ".previous"
            print("当前 3dsx 不是官方原版，另存 ->", os.path.basename(prev))
            if not dry:
                shutil.copy2(target, prev)
        print("用包内官方原版建立备份 ->", os.path.basename(backup))
        if not dry:
            shutil.copy2(STOCK, backup)
    else:
        print("备份已存在，跳过:", os.path.basename(backup))

    print("覆盖 ->", target)
    if not dry:
        shutil.copy2(source, target)
    if os.path.isfile(log):
        print("删除旧日志 boot-log.txt")
        if not dry:
            os.remove(log)

    if not dry:
        ok = os.path.getsize(target) == os.path.getsize(source) and sha(target) == source_hash
        print("校验:", "OK" if ok else "失败")

    print("\n接下来在 3DS 上：")
    print("  1. 安全弹出 SD 卡，插回 3DS，开机。")
    print("  2. 进 Homebrew Launcher（不要用 CIA 图标），选 SMG-3DS 启动。")
    print("  3. 下屏出现 'SMG boot bring-up' 正常；真机约 14 fps，耐心等 1-3 分钟。")
    if fps or clipfix:
        print("  4. 这个版本强制走美版验证过的英语 BMG，并在下屏固定一行显示")
        print("     FPS / 每帧毫秒 / 窗口内最慢帧 / 累计帧数（每 0.5 秒刷新）。")
        print("  5. 想关掉显示：在 settings.ini 加一行 dev.show_fps=0 后重启。")
        print("     若仍退出，boot-log.txt 会写出新的原因，发我。")
    if clipfix:
        print("  6. 实验构建：2D/JPA 条纹也走 CPU 近平面裁剪，真机效果未验证。")
        print("     若画面或帧率变差，用 --fps 装回对照版，并把对比结果发我。")
    elif english:
        print("  4. 这个版本强制走美版验证过的英语 BMG，理论上不会再 abort，")
        print("     应该能进标题画面。若仍退出，boot-log.txt 会写出新的原因，发我。")
    else:
        print("  4. 等它自己退出/重启，中途别按 HOME、别断电。")
        print("  5. 关机拔卡插回电脑，把 SD:\\3ds\\SMG-3DS\\boot-log.txt 发出来。")
    print("  用完恢复原版: py -3 install-diag.py", dest.rstrip("\\/"), "--restore")
    return 0


if __name__ == "__main__":
    sys.exit(main())
