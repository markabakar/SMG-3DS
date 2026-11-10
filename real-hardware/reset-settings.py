#!/usr/bin/env python3
"""Remove every dev.* experiment line from the SD card's settings.ini.

    py -3 reset-settings.py --list       list drives
    py -3 reset-settings.py F: --dry-run preview
    py -3 reset-settings.py F:          remove dev.* lines (backs up once)

Only the dev.* lines are removed; your key bindings, pointer mode and speeds
are left exactly as they are. The original is kept as settings.ini.bak.
"""
import os
import shutil
import sys


def list_drives():
    import ctypes
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    types = {0: "unknown", 2: "removable", 3: "local", 4: "network", 5: "cdrom", 6: "ram"}
    print("Drives:")
    for i in range(26):
        if not (bitmask >> i) & 1:
            continue
        root = "{}:\\".format(chr(ord("A") + i))
        t = ctypes.windll.kernel32.GetDriveTypeW(root)
        try:
            free = "{:.1f} GiB free".format(shutil.disk_usage(root).free / 1024 ** 3)
        except OSError:
            free = ""
        print("  {}  {:<10} {}".format(root, types.get(t, "?"), free))


def main():
    args = sys.argv[1:]
    if "--list" in args or not args:
        list_drives()
        return 0
    dry = "--dry-run" in args
    dest = next((a for a in args if not a.startswith("--")), None)
    if not dest:
        print("Usage: py -3 reset-settings.py <drive> [--dry-run]")
        return 1
    if len(dest) == 2 and dest[1] == ":":
        dest += "\\"
    if not os.path.isdir(dest):
        print("Drive not found:", dest)
        return 1
    if os.path.abspath(dest).upper().startswith("C:\\"):
        print("Refusing to touch C:")
        return 1
    target = os.path.join(dest, "3ds", "SMG-3DS", "settings.ini")
    if not os.path.isfile(target):
        print("Not found:", target)
        return 1

    with open(target, encoding="utf-8", errors="surrogateescape", newline="") as f:
        lines = f.readlines()
    dev = [l.rstrip("\r\n") for l in lines if l.lstrip().startswith("dev.")]
    print("settings.ini:", os.path.abspath(target))
    if not dev:
        print("No dev.* lines found - settings are already clean, nothing to do.")
        return 0
    print("dev.* lines to remove:")
    for l in dev:
        print("   ", l)
    if dry:
        print("(dry run, nothing written)")
        return 0

    backup = target + ".bak"
    if not os.path.isfile(backup):
        shutil.copy2(target, backup)
        print("Backup ->", os.path.basename(backup))
    kept = [l for l in lines if not l.lstrip().startswith("dev.")]
    with open(target, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.writelines(kept)
    print("Removed {} dev.* line(s). Key bindings / pointer / speeds untouched.".format(len(dev)))
    print("Safely eject, put the card back in the 3DS and restart the game.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
